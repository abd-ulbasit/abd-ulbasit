#!/usr/bin/env python3
"""Prove that verify_links.py fails when the repository is actually wrong.

A checker nobody has ever seen fail is indistinguishable from a checker that
returns 0 unconditionally. Every test here takes a throwaway copy of the real
working tree, breaks exactly one thing in it, and asserts that the script
notices. Two of them break the site the way it was already broken before the
checks existed: a canonical tag naming the apex while the server serves www,
and a page with no og:image.

Nothing here touches the repository. The tree under test is a copy in a
temporary directory, and the script itself only ever reads.

    python3 scripts/test_verify_links.py

No test uses the network. The structural ones run the checker with --offline;
the ones that exercise the fetching half replace verify_links.fetch with canned
answers, which is also the only way to test a link going dead on purpose.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verify_links  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = shutil.ignore_patterns(".git", "__pycache__", ".playwright-mcp", "node_modules")


class CheckerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="verify-links-")
        self.root = os.path.join(self.tmp, "site")
        shutil.copytree(REPO, self.root, ignore=SKIP)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_checker(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = verify_links.main(["--root", self.root, *extra])
        return status, out.getvalue()

    def path(self, rel):
        return os.path.join(self.root, rel)

    def edit(self, rel, old, new):
        with open(self.path(rel), encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn(old, body, "%s no longer contains %r" % (rel, old))
        with open(self.path(rel), "w", encoding="utf-8") as handle:
            handle.write(body.replace(old, new, 1))

    def assertFails(self, needle, *extra):
        status, output = self.run_checker("--offline", *extra)
        self.assertEqual(status, 1, "expected a non-zero exit\n" + output)
        self.assertIn(needle, output)
        return output


class TheTreeAsItStandsPasses(CheckerCase):
    def test_unmodified_copy_passes_offline(self):
        status, output = self.run_checker("--offline")
        self.assertEqual(status, 0, output)


class BrokenLinks(CheckerCase):
    def test_relative_link_to_a_missing_file(self):
        self.edit("index.html", 'href="work/pgbranch.html"', 'href="work/pgbrnach.html"')
        self.assertFails("no such file")

    def test_renaming_a_page_breaks_the_pages_that_link_to_it(self):
        os.rename(self.path("work/pgbranch.html"), self.path("work/pgbranch-v2.html"))
        self.assertFails("no such file")

    def test_root_relative_asset_that_does_not_exist(self):
        os.remove(self.path("favicon.ico"))
        self.assertFails("no such file")

    def test_fragment_with_no_matching_id(self):
        self.edit("index.html", 'href="#main"', 'href="#mian"')
        self.assertFails("no id='mian'")


class BrokenSocialAndCanonicalTags(CheckerCase):
    def test_canonical_naming_the_apex_the_server_redirects_away_from(self):
        self.edit(
            "index.html",
            '<link rel="canonical" href="https://www.basit.engineer/" />',
            '<link rel="canonical" href="https://basit.engineer/" />',
        )
        self.assertFails("canonical disagrees with where the page is served")

    def test_og_url_left_on_the_wrong_page(self):
        self.edit(
            "work/pgbranch.html",
            "https://www.basit.engineer/work/pgbranch.html",
            "https://www.basit.engineer/work/real-time-inference.html",
        )
        self.assertFails("og:url disagrees with where the page is served")

    def test_page_with_no_og_image_shares_as_text(self):
        self.edit(
            "index.html",
            '      property="og:image"\n'
            '      content="https://www.basit.engineer/assets/og-card.png"\n',
            '      property="og:image:removed"\n'
            '      content="https://www.basit.engineer/assets/og-card.png"\n',
        )
        self.assertFails("declares no og:image")

    def test_og_image_file_that_is_not_there(self):
        os.remove(self.path("assets/og-card.png"))
        self.assertFails("og:image has no file")


PINNED = ("https://github.com/abd-ulbasit/goqueue/blob/"
          "beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go#L1121")
BENCH_HEADING = "Before the fix: branch creation scaled with data size"


def canned_fetch(**responses):
    """A stand-in for verify_links.fetch, so the network checks can be tested.

    Everything answers 200 unless named. The two raw.githubusercontent bodies
    are the ones the fragment checks read: the pinned line the README quotes,
    and the heading the benchmarks anchor points at.
    """
    line = verify_links.ASSERTIONS[PINNED]

    def fetch(url):
        if url in responses:
            return responses[url]
        if url.endswith("/internal/storage/segment.go"):
            return 200, "\n" * 1120 + line + "\n"
        if url.endswith("/docs/benchmarks.md"):
            return 200, "## %s\n" % BENCH_HEADING
        return 200, ""

    return fetch


class NetworkChecks(CheckerCase):
    """The fetching half, with fetch replaced, so these stay offline and stable."""

    def use(self, fetch):
        original = verify_links.fetch
        verify_links.fetch = fetch
        self.addCleanup(setattr, verify_links, "fetch", original)

    def test_the_canned_healthy_answers_pass(self):
        self.use(canned_fetch())
        status, output = self.run_checker()
        self.assertEqual(status, 0, output)

    def test_dead_third_party_link(self):
        dead = "https://github.com/abd-ulbasit/pgbranch"
        self.use(canned_fetch(**{dead: (404, "")}))
        status, output = self.run_checker()
        self.assertEqual(status, 1, output)
        self.assertIn("HTTP 404  " + dead, output)

    def test_bot_block_is_a_note_not_a_failure(self):
        blocked = "https://www.linkedin.com/in/abd-ulbasit/"
        self.use(canned_fetch(**{blocked: (999, "")}))
        status, output = self.run_checker()
        self.assertEqual(status, 0, output)
        self.assertIn("bot-blocked", output)

    def test_pinned_line_that_now_says_something_else(self):
        raw = ("https://raw.githubusercontent.com/abd-ulbasit/goqueue/"
               "beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go")
        self.use(canned_fetch(**{raw: (200, "\n" * 1120 + "// something else\n")}))
        status, output = self.run_checker()
        self.assertEqual(status, 1, output)
        self.assertIn("line 1121 changed", output)

    def test_pinned_line_past_the_end_of_a_shortened_file(self):
        raw = ("https://raw.githubusercontent.com/abd-ulbasit/goqueue/"
               "beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go")
        self.use(canned_fetch(**{raw: (200, "package storage\n")}))
        status, output = self.run_checker()
        self.assertEqual(status, 1, output)
        self.assertIn("past end of file", output)

    def test_markdown_anchor_whose_heading_was_renamed(self):
        raw = ("https://raw.githubusercontent.com/abd-ulbasit/pgbranch/"
               "main/docs/benchmarks.md")
        self.use(canned_fetch(**{raw: (200, "## Some other heading\n")}))
        status, output = self.run_checker()
        self.assertEqual(status, 1, output)
        self.assertIn("no heading matches", output)


class SitemapAndRobots(CheckerCase):
    def test_new_page_missing_from_the_sitemap(self):
        shutil.copy(self.path("work/pgbranch.html"), self.path("work/pgbranch-part-2.html"))
        self.assertFails("sitemap.xml does not list")

    def test_sitemap_listing_a_page_that_no_longer_exists(self):
        self.edit(
            "sitemap.xml",
            "<loc>https://www.basit.engineer/work/pgbranch.html</loc>",
            "<loc>https://www.basit.engineer/work/pgbranch-old.html</loc>",
        )
        self.assertFails("which is not a page in this repository")

    def test_sitemap_on_the_wrong_host(self):
        self.edit(
            "sitemap.xml",
            "<loc>https://www.basit.engineer/</loc>",
            "<loc>https://basit.engineer/</loc>",
        )
        self.assertFails("sitemap.xml does not list https://www.basit.engineer/")

    def test_robots_pointing_at_no_sitemap(self):
        self.edit("robots.txt", "Sitemap: https://www.basit.engineer/sitemap.xml", "")
        self.assertFails("robots.txt does not point at")


class NothingPublishedByAccident(CheckerCase):
    def test_a_source_file_no_rule_covers(self):
        # *.toml is not in .vercelignore, so this one would be a public URL.
        with open(self.path("pyproject.toml"), "w", encoding="utf-8") as handle:
            handle.write("[tool.whatever]\n")
        self.assertFails(".vercelignore does not exclude it")

    def test_source_file_in_a_new_directory(self):
        os.mkdir(self.path("notes"))
        with open(self.path("notes/plan.sql"), "w", encoding="utf-8") as handle:
            handle.write("select 1;\n")
        self.assertFails("notes/plan.sql is served at")

    def test_no_vercelignore_at_all(self):
        os.remove(self.path(".vercelignore"))
        self.assertFails("no .vercelignore")

    def test_a_rule_form_the_check_cannot_read_is_not_accepted_silently(self):
        # Naming one file is the patch that this whole check exists to replace.
        with open(self.path(".vercelignore"), "a", encoding="utf-8") as handle:
            handle.write("posts/DRAFT.md\n")
        self.assertFails("is a form this check cannot read")


if __name__ == "__main__":
    unittest.main(verbosity=2)
