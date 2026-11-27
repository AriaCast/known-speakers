import os
import subprocess
import sys
import unittest

from helpers import HERE, lib

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import render_readme  # noqa: E402

ROOT = os.path.dirname(HERE)


class Readme(unittest.TestCase):
    def doc(self):
        return {"schema": 2, "version": 9, "updated": "x", "speakers": [
            {"id": "a-a-a", "speaker": "Pipe | Speaker", "protocol": "DLNA", "status": "supported", "match": {"mentions": ["pipe"]},
             "evidence": "e", "locked": True, "reports": {"supported": 3, "unsupported": 1}},
            {"id": "b-b-b", "speaker": "Odd", "protocol": "DLNA", "status": "unsupported", "match": {"mentions": ["odd"]},
             "symptoms": ["one", "two"], "whatToDo": "Wait", "evidence": "e"},
        ]}

    def test_groups_by_status_and_says_when_a_group_is_empty(self):
        text = render_readme.render(self.doc())
        self.assertLess(text.index("## Supported\n"), text.index("## Supported with quirks"))
        self.assertLess(text.index("## Supported with quirks"), text.index("## Unsupported"))
        self.assertIn("Nothing recorded yet.", text)

    def test_cells_are_escaped_and_marked(self):
        text = render_readme.render(self.doc())
        self.assertIn("Pipe \\| Speaker 🔒", text)
        self.assertIn("3 supported, 1 unsupported", text)
        self.assertIn("one<br>two", text)

    def test_the_version_is_in_the_header(self):
        self.assertIn("list version 9", render_readme.render(self.doc()))

    def test_the_committed_readme_is_current(self):
        result = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "scripts", "render_readme.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
