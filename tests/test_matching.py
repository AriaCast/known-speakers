"""The cases the apps and the bot must answer the same way (tests/data/matching-cases.json).

The same file sits in AriaCast-app's test resources, where a Kotlin test runs the same cases
against the app's own matching code. If one side's rule changes, the file changes, and the other
side's test fails until it is brought along.
"""
import json
import os
import unittest

from helpers import DATA, lib

with open(os.path.join(DATA, "matching-cases.json"), encoding="utf-8") as f:
    CASES = json.load(f)


class SharedCases(unittest.TestCase):
    def test_the_list_is_valid(self):
        self.assertEqual(lib.validate(CASES["list"]), [])

    def test_every_case(self):
        for case in CASES["cases"]:
            with self.subTest(case["why"]):
                self.assertEqual([e["id"] for e in lib.matching(CASES["list"], case["device"])], case["matches"])
                best = lib.best_match(CASES["list"], case["device"])
                self.assertEqual(best["id"] if best else None, case["best"])

    def test_the_cases_are_not_trivial(self):
        # A file of cases that all say "nothing matches" would prove nothing.
        self.assertGreater(sum(1 for c in CASES["cases"] if c["best"]), 6)
        self.assertGreater(sum(1 for c in CASES["cases"] if not c["best"]), 2)
        self.assertTrue(any(len(c["matches"]) > 1 for c in CASES["cases"]), "no case where specificity decides")


if __name__ == "__main__":
    unittest.main()
