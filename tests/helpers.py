import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import report  # noqa: E402
import speakers_lib as lib  # noqa: E402

DATA = os.path.join(HERE, "data")


def read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return f.read()


def form(speaker="Acme Play 3", protocol="DLNA", status="Supported with quirks", happens="It stops", details="", log=""):
    return (
        "### Speaker\n\n%s\n\n### Protocol\n\n%s\n\n### How does it work?\n\n%s\n\n### What happens\n\n%s\n\n"
        "### Speaker details\n\n%s\n\n### Log\n\n%s\n\n### AriaCast version\n\n2.0.0\n"
    ) % (speaker, protocol, status, happens, details, log)


class Run:
    """Runs the bot the way the workflow does, on a copy of a list."""

    def __init__(self, body, number="77", repo="AriaCast/known-speakers", base="base.json", today=0):
        self.dir = tempfile.mkdtemp()
        self.data = os.path.join(self.dir, "speakers.json")
        self.comment = os.path.join(self.dir, "comment.md")
        self.output = os.path.join(self.dir, "output")
        shutil.copy(os.path.join(DATA, base), self.data)
        self.before = read(base)
        env = {"ISSUE_BODY": body, "ISSUE_NUMBER": number, "GITHUB_REPOSITORY": repo, "GITHUB_OUTPUT": self.output,
               "SPEAKER_REPORT_TODAY": "2026-11-27", "AUTHOR_REPORTS_TODAY": str(today)}
        report.main(["x", self.data, self.comment], env)

    def doc(self):
        return json.loads(self.text())

    def text(self):
        with open(self.data, encoding="utf-8") as f:
            return f.read()

    def readme(self):
        path = os.path.join(self.dir, "README.md")
        return open(path, encoding="utf-8").read() if os.path.exists(path) else None

    def said(self):
        with open(self.comment, encoding="utf-8") as f:
            return f.read()

    def result(self):
        with open(self.output, encoding="utf-8") as f:
            return f.read().strip().split("=", 1)[1]

    def untouched(self):
        return self.text() == self.before and self.readme() is None

    def entry(self, entry_id):
        return next(e for e in self.doc()["speakers"] if e["id"] == entry_id)
