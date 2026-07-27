#!/usr/bin/env python3
"""Check that everything in this repository that points somewhere still lands there.

This replaces the old daily stats pipeline (today.py + generate_svg.py), which
wrote to the README on a cron and produced 34 of this repository's first 65
commits without ever saying anything. The difference that matters:

    this script never writes to the repository.

It reads, it checks, and it exits non-zero. The workflow turns a non-zero exit
into an issue. A generator that dies silently leaves a wrong README rendering
as if it were right; a checker that dies silently leaves the README exactly as
its author last wrote it. That asymmetry is the whole design.

It covers two surfaces, because the repository root is also the web root:
README.md, and every .html page served at basit.engineer.

Checks, in increasing order of how much they actually prove:

  1. Every third-party http(s) link resolves (not 4xx/5xx).
  2. Every GitHub blob link carrying a `#L<n>` fragment has a line n, and where
     ASSERTIONS names the expected text, line n still *is* that text. A link
     that returns 200 while pointing at the wrong line after a refactor is the
     specific failure this catches, and the reason the link is pinned to a
     commit SHA rather than a branch.
  3. Every markdown `#anchor` fragment matches a heading that GitHub would
     actually slugify to that anchor. GitHub serves 200 for a fragment that
     matches nothing, so status alone proves nothing here.
  4. Every relative href/src in a page resolves to a file in this repository,
     and every `#fragment` matches an id that exists on the page it points at.
  5. Every page declares a canonical URL and an og:url, both equal to the URL
     that page is actually served at, and an og:image that exists. Two of those
     are not link rot, they are the two ways this site has already been wrong:
     tags that named the apex while the server redirects to www, and shares
     that unfurled as text because no image was ever declared.
  6. sitemap.xml lists every page and nothing else, and robots.txt points at it.

Links to this site's own URLs are resolved against the working tree, not
fetched. Fetching them would make a push race the deploy that satisfies it, and
file-in-the-repo is the stronger claim anyway.

Standard library only, no auth. Run it locally the same way CI does:

    python3 scripts/verify_links.py

Two flags exist for the tests in scripts/test_verify_links.py, which run it
against a throwaway copy of the tree:

    --root DIR   check DIR instead of the repository this script lives in
    --offline    skip the network checks and prove the structural ones
"""

import argparse
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

SITE = "https://www.basit.engineer"

UA = {"User-Agent": "abd-ulbasit-link-verify (+https://github.com/abd-ulbasit)"}
TIMEOUT = 30

# Statuses that mean "you are not a browser", not "this link is dead".
# LinkedIn answers 999 to anything without a browser fingerprint. A link that
# has actually rotted answers 404 or 410, and those still fail.
BOT_BLOCKED = {403, 429, 999}

# Line-level assertions for SHA-pinned links. The README quotes these lines, so
# a 200 that points at different text is a silent falsehood in a file whose
# entire argument is that it does not contain any.
ASSERTIONS = {
    "https://github.com/abd-ulbasit/goqueue/blob/beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go#L1121":
        "// Note: We need to unlock before calling ReadFrom (it locks again)",
}

LINK_DEF = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
LINK_INLINE = re.compile(r"\]\((https?://[^)\s]+)\)")
BLOB = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)(?:#(.+))?$")

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
IGNORED_SCHEMES = ("mailto:", "tel:", "javascript:", "data:")


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

def fetch(url):
    """GET a URL, returning (status, body). Raises on transport failure."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""


def slugify(heading):
    """Approximate GitHub's heading-to-anchor rule."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"[\s_]+", "-", slug).strip("-")


def raw_url(owner, repo, ref, path):
    return "https://raw.githubusercontent.com/%s/%s/%s/%s" % (owner, repo, ref, path)


def check_url(url, where, failures, notes):
    """Check one third-party URL, plus its fragment if it is a GitHub blob link."""
    status, _ = fetch(url)
    if status in BOT_BLOCKED:
        notes.append("HTTP %d (bot-blocked, not treated as rot)  %s" % (status, url))
        return
    if status >= 400:
        failures.append("HTTP %d  %s  [%s]" % (status, url, where))
        return

    match = BLOB.match(url)
    if not match:
        return
    owner, repo, ref, path, fragment = match.groups()
    if not fragment:
        return

    status, body = fetch(raw_url(owner, repo, ref, path))
    if status >= 400:
        failures.append("raw fetch HTTP %d for fragment #%s  %s" % (status, fragment, url))
        return
    lines = body.splitlines()

    line_ref = re.fullmatch(r"L(\d+)", fragment)
    if line_ref:
        n = int(line_ref.group(1))
        if n > len(lines):
            failures.append("#L%d past end of file (%d lines)  %s" % (n, len(lines), url))
            return
        expected = ASSERTIONS.get(url)
        actual = lines[n - 1].strip()
        if expected and actual != expected:
            failures.append(
                "line %d changed  %s\n      expected: %s\n      found:    %s"
                % (n, url, expected, actual)
            )
        return

    if path.endswith(".md"):
        anchors = {slugify(m) for m in re.findall(r"^#{1,6}\s+(.+)$", body, re.MULTILINE)}
        if fragment not in anchors:
            failures.append("no heading matches #%s  %s" % (fragment, url))


# --------------------------------------------------------------------------
# the site
# --------------------------------------------------------------------------

class Page(HTMLParser):
    """Everything one page claims: what it links to, what ids it has, its meta."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []       # (value, description of where it came from)
        self.ids = set()
        self.meta = {}        # og:url / twitter:card / ... -> content
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        attr = {k.lower(): (v or "") for k, v in attrs}
        if attr.get("id"):
            self.ids.add(attr["id"])
        if tag == "a" and attr.get("href"):
            self.links.append((attr["href"], "a href"))
        elif tag == "link" and attr.get("href"):
            rel = attr.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = attr["href"]
            else:
                self.links.append((attr["href"], "link rel=%s" % (rel or "?")))
        elif tag in ("script", "img", "source", "iframe") and attr.get("src"):
            self.links.append((attr["src"], "%s src" % tag))
        elif tag == "meta":
            key = (attr.get("property") or attr.get("name") or "").lower()
            if key and attr.get("content"):
                self.meta[key] = attr["content"]


def html_files(root):
    """Every page this repository serves, repo-relative, in a stable order."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(found)


def page_url(rel):
    """The URL a page file is served at."""
    rel = rel.replace(os.sep, "/")
    if os.path.basename(rel) == "index.html":
        parent = os.path.dirname(rel)
        return SITE + "/" + (parent + "/" if parent else "")
    return SITE + "/" + rel


def local_target(url):
    """Repo-relative path for one of this site's own URLs, or None if third-party."""
    if not url.startswith(SITE + "/"):
        return None
    path = urllib.parse.urlsplit(url).path
    if path.endswith("/"):
        path += "index.html"
    return path.lstrip("/")


def read_page(path):
    parser = Page()
    with open(path, encoding="utf-8") as handle:
        parser.feed(handle.read())
    return parser


def check_fragment(target_rel, fragment, where, root, failures, pages):
    """A #fragment has to match an id on the page it points at."""
    page = pages.get(target_rel)
    if page is None:
        if not os.path.exists(os.path.join(root, target_rel)):
            return
        page = read_page(os.path.join(root, target_rel))
        pages[target_rel] = page
    if fragment not in page.ids:
        failures.append("no id=%r on %s  [%s]" % (fragment, target_rel, where))


def check_page_links(rel, page, root, external, failures, pages):
    """Relative and root-relative links resolve; own-site links resolve; #ids exist."""
    here = os.path.dirname(rel)
    for value, kind in page.links:
        where = "%s %s" % (rel, kind)
        if value.startswith(IGNORED_SCHEMES):
            continue

        if value.startswith("http://") or value.startswith("https://"):
            target = local_target(value)
            if target is None:
                external.setdefault(value, where)
            elif not os.path.exists(os.path.join(root, target)):
                failures.append("own-site link has no file  %s  [%s]" % (value, where))
            continue

        path, _, fragment = value.partition("#")
        if not path:
            if fragment and fragment not in page.ids:
                failures.append("no id=%r on %s  [%s]" % (fragment, rel, where))
            continue

        if path.startswith("/"):
            target = os.path.normpath(path.lstrip("/"))
        else:
            target = os.path.normpath(os.path.join(here, path))
        if target.startswith(".."):
            failures.append("link escapes the site root  %s  [%s]" % (value, where))
            continue
        if not os.path.exists(os.path.join(root, target)):
            failures.append("no such file  %s -> %s  [%s]" % (value, target, where))
            continue
        if fragment and target.endswith(".html"):
            check_fragment(target, fragment, where, root, failures, pages)


def check_page_meta(rel, page, root, failures):
    """canonical, og:url and og:image: the three tags a share depends on."""
    expected = page_url(rel)

    if page.canonical is None:
        failures.append("%s declares no canonical URL" % rel)
    elif page.canonical != expected:
        failures.append(
            "%s canonical disagrees with where the page is served\n"
            "      declared: %s\n      served:   %s" % (rel, page.canonical, expected)
        )

    og_url = page.meta.get("og:url")
    if og_url is None:
        failures.append("%s declares no og:url" % rel)
    elif og_url != expected:
        failures.append(
            "%s og:url disagrees with where the page is served\n"
            "      declared: %s\n      served:   %s" % (rel, og_url, expected)
        )

    og_image = page.meta.get("og:image")
    if og_image is None:
        failures.append("%s declares no og:image, so every share of it is a text card" % rel)
        return
    target = local_target(og_image)
    if target is None:
        failures.append(
            "%s og:image is not an absolute URL on this site: %s" % (rel, og_image)
        )
    elif not os.path.exists(os.path.join(root, target)):
        failures.append("%s og:image has no file: %s" % (rel, og_image))


def check_sitemap(root, pages_rel, failures):
    # ElementTree, not defusedxml: the input is this repository's own
    # sitemap.xml, and the stdlib-only rule is what keeps this script
    # runnable with nothing installed.
    path = os.path.join(root, "sitemap.xml")
    if not os.path.exists(path):
        failures.append("no sitemap.xml")
        return
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        failures.append("sitemap.xml does not parse: %s" % exc)
        return

    listed = {node.text.strip() for node in tree.iter(SITEMAP_NS + "loc") if node.text}
    expected = {page_url(rel) for rel in pages_rel}
    for url in sorted(expected - listed):
        failures.append("sitemap.xml does not list %s" % url)
    for url in sorted(listed - expected):
        failures.append("sitemap.xml lists %s, which is not a page in this repository" % url)


def check_robots(root, failures):
    path = os.path.join(root, "robots.txt")
    if not os.path.exists(path):
        failures.append("no robots.txt")
        return
    with open(path, encoding="utf-8") as handle:
        body = handle.read()
    wanted = SITE + "/sitemap.xml"
    if wanted not in body:
        failures.append("robots.txt does not point at %s" % wanted)


# --------------------------------------------------------------------------

def readme_urls(root, failures):
    path = os.path.join(root, "README.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    urls = {u for u in LINK_DEF.findall(text) + LINK_INLINE.findall(text)
            if u.startswith("http")}
    if not urls:
        failures.append("no links found in README.md, which is itself suspicious")
    return urls


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.path.dirname(here),
                        help="directory to check (default: this repository)")
    parser.add_argument("--offline", action="store_true",
                        help="skip the network checks, run the structural ones")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    failures = []
    notes = []
    external = {}

    for url in readme_urls(root, failures):
        external.setdefault(url, "README.md")

    pages_rel = html_files(root)
    if not pages_rel:
        failures.append("no .html pages found under %s, which is itself suspicious" % root)

    pages = {rel: read_page(os.path.join(root, rel)) for rel in pages_rel}
    for rel in pages_rel:
        check_page_links(rel, pages[rel], root, external, failures, pages)
        check_page_meta(rel, pages[rel], root, failures)

    check_sitemap(root, pages_rel, failures)
    check_robots(root, failures)

    print("%d page(s): %s" % (len(pages_rel), ", ".join(pages_rel)))
    print("%d third-party link(s) in README.md and those pages:" % len(external))
    for url in sorted(external):
        print("  %s" % url)

    if args.offline:
        print("\n--offline: structural checks only, nothing was fetched")
    else:
        for url in sorted(external):
            check_url(url, external[url], failures, notes)

    for note in notes:
        print("\nnote: %s" % note)

    if failures:
        print("\n%d problem(s):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1

    if args.offline:
        print("\nevery page names the URL it is served at and every local target"
              " exists; nothing was fetched, so nothing is claimed about the"
              " third-party links above")
    else:
        print("\nevery link resolves, every page names the URL it is served at,"
              " and the pinned lines and anchors still say what is quoted of them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
