#!/usr/bin/env python3
"""Check that every claim in README.md that points somewhere still lands there.

This replaces the old daily stats pipeline (today.py + generate_svg.py), which
wrote to the README on a cron and produced 34 of this repository's first 65
commits without ever saying anything. The difference that matters:

    this script never writes to the repository.

It reads, it checks, and it exits non-zero. The workflow turns a non-zero exit
into an issue. A generator that dies silently leaves a wrong README rendering
as if it were right; a checker that dies silently leaves the README exactly as
its author last wrote it. That asymmetry is the whole design.

Three checks, in increasing order of how much they actually prove:

  1. Every http(s) link resolves (not 4xx/5xx).
  2. Every GitHub blob link carrying a `#L<n>` fragment has a line n, and where
     ASSERTIONS names the expected text, line n still *is* that text. A link
     that returns 200 while pointing at the wrong line after a refactor is the
     specific failure this catches, and the reason the link is pinned to a
     commit SHA rather than a branch.
  3. Every markdown `#anchor` fragment matches a heading that GitHub would
     actually slugify to that anchor. GitHub serves 200 for a fragment that
     matches nothing, so status alone proves nothing here.

Standard library only, no auth. Run it locally the same way CI does:

    python3 scripts/verify_links.py
"""

import re
import sys
import urllib.error
import urllib.request

README = "README.md"
UA = {"User-Agent": "abd-ulbasit-link-verify (+https://github.com/abd-ulbasit)"}
TIMEOUT = 30

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


def check(url, failures):
    status, _ = fetch(url)
    if status >= 400:
        failures.append("HTTP %d  %s" % (status, url))
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


def main():
    with open(README, encoding="utf-8") as handle:
        text = handle.read()

    urls = sorted({u for u in LINK_DEF.findall(text) + LINK_INLINE.findall(text)
                   if u.startswith("http")})
    if not urls:
        print("no links found in %s, which is itself suspicious" % README)
        return 1

    failures = []
    for url in urls:
        check(url, failures)

    print("checked %d links in %s" % (len(urls), README))
    for url in urls:
        print("  %s" % url)

    if failures:
        print("\n%d problem(s):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1

    print("\nall links resolve, all pinned lines and anchors still say what the README quotes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
