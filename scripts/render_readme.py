#!/usr/bin/env python3
"""Write README.md from speakers.json, or check that it is up to date (--check).

    python3 scripts/render_readme.py            rewrite README.md
    python3 scripts/render_readme.py --check    fail if README.md is out of date
"""
import os
import sys

import speakers_lib as lib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEADER = """# Known speakers

How speakers behave with [AriaCast](https://github.com/AriaCast/AriaCast-app), what you see when
something is wrong, and what to do. The AriaCast app reads this list (Settings → Known speakers)
and keeps it up to date.

Only behavior somebody reported or a maintainer checked is listed; a speaker that is not here is
untested, not broken. A status follows the most reported one, so one report does not flip a speaker.
Entries marked 🔒 are curated by a maintainer: reports are counted but do not change them.

<!-- Generated from speakers.json (list version {version}). Do not edit by hand: the bot and
     `python3 scripts/render_readme.py` keep it current. -->

"""

FOOTER = """## Add or confirm a speaker

In the app, answer the question that appears the first time you cast to a new speaker, or
long-press a speaker and choose **Report speaker**. It opens a pre-filled
[report](../../issues/new?template=speaker-report.yml). If the speaker is already here, your report
is counted; if not, it is added. See [docs/SCHEMA.md](docs/SCHEMA.md) for the file's format.
"""


def cell(text):
    return (text or "").replace("|", "\\|").replace("\n", " ")


def reports(entry):
    counts = entry.get("reports", {})
    return ", ".join("%d %s" % (counts[s], lib.STATUS_LABELS[s].lower()) for s in lib.STATUSES if counts.get(s))


def render(doc):
    out = [HEADER.format(version=doc["version"])]
    for status in lib.STATUSES:
        rows = [e for e in doc["speakers"] if e["status"] == status]
        out.append("## %s\n\n" % lib.STATUS_LABELS[status])
        if not rows:
            out.append("Nothing recorded yet.\n\n")
            continue
        out.append("| Speaker | Protocol | If it goes wrong | What to do | Reports | Evidence |\n|---|---|---|---|---|---|\n")
        for e in rows:
            name = cell(e["speaker"]) + (" 🔒" if e.get("locked") else "")
            out.append("| %s | %s | %s | %s | %s | %s |\n" % (
                name, cell(e["protocol"]), cell("<br>".join(e.get("symptoms", []))),
                cell(e.get("whatToDo")), cell(reports(e)), cell(e["evidence"])))
        out.append("\n")
    out.append(FOOTER)
    return "".join(out)


def main(argv):
    doc = lib.load(os.path.join(ROOT, "speakers.json"))
    text = render(doc)
    path = os.path.join(ROOT, "README.md")
    if "--check" in argv:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if current != text:
            print("README.md is out of date: run python3 scripts/render_readme.py")
            return 1
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
