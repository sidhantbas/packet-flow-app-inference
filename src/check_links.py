"""Check relative links in every tracked Markdown file (results/ run reports are immutable and skipped).

Usage: .venv/bin/python src/check_links.py [--quiet]    exit 1 if any relative link points to a missing file
External links (http, https, mailto) and pure anchors (#...) are not checked; anchors after a path are ignored.
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
CODE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")


def tracked_markdown():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [ROOT / f for f in out if not f.startswith("results/")]


def broken_links(path):
    text = INLINE.sub("", CODE.sub("", path.read_text(errors="replace")))
    bad = []
    for m in LINK.finditer(text):
        target = m.group(1) or m.group(2)
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        rel = unquote(target.split("#")[0])
        if rel and not (path.parent / rel).exists():
            bad.append(target)
    return bad


def main():
    total, issues = 0, {}
    for p in tracked_markdown():
        total += 1
        b = broken_links(p)
        if b:
            issues[str(p.relative_to(ROOT))] = b
    n = sum(len(v) for v in issues.values())
    if "--quiet" not in sys.argv:
        for f, links in sorted(issues.items()):
            for l in links:
                print(f"{f}: {l}")
    print(f"checked {total} Markdown files: {n} broken relative links in {len(issues)} files")
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
