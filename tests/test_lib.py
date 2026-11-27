import copy
import os
import unittest

from helpers import DATA, lib


def good():
    return copy.deepcopy(lib.load(os.path.join(DATA, "base.json")))


class Validate(unittest.TestCase):
    def broken(self, change):
        doc = good()
        change(doc)
        return lib.validate(doc)

    def test_a_good_list(self):
        self.assertEqual(lib.validate(good()), [])

    def test_the_real_list(self):
        self.assertEqual(lib.validate(lib.load(os.path.join(os.path.dirname(DATA), "..", "speakers.json"))), [])

    def test_top_level_rules(self):
        self.assertTrue(self.broken(lambda d: d.update(schema=1)))
        self.assertTrue(self.broken(lambda d: d.update(version=-1)))
        self.assertTrue(self.broken(lambda d: d.update(version="3")))
        self.assertTrue(self.broken(lambda d: d.update(speakers={})))
        self.assertTrue(lib.validate([]))

    def test_each_entry_rule(self):
        e = lambda d: d["speakers"][1]  # noqa: E731
        for change in (
            lambda d: e(d).update(id="BAD ID"),
            lambda d: e(d).update(id="wiim-dlna-restart"),
            lambda d: e(d).update(speaker=" "),
            lambda d: e(d).update(protocol=""),
            lambda d: e(d).update(evidence=""),
            lambda d: e(d).update(status="great"),
            lambda d: e(d).update(match={"mentions": []}),
            lambda d: e(d).update(match={"mentions": ["ab"]}),
            lambda d: e(d).update(match={"mentions": ["UPPER"]}),
            lambda d: e(d).update(match={"mentions": ["???"]}),
            lambda d: e(d).update(symptoms="text"),
            lambda d: e(d).update(status="quirks"),  # needs symptoms
            lambda d: e(d).update(reports={"great": 1}),
            lambda d: e(d).update(reports={"supported": -1}),
            lambda d: e(d).update(reports={"supported": True}),
            lambda d: e(d).update(reports={"supported": 10**9}),
        ):
            self.assertTrue(self.broken(change), change)

    def test_config_is_limited_to_the_known_knobs(self):
        e = lambda d: d["speakers"][1]  # noqa: E731
        self.assertEqual(self.broken(lambda d: e(d).update(config={"sendMetadata": False, "defaultDelayMs": 300})), [])
        self.assertTrue(self.broken(lambda d: e(d).update(config={"anything": 1})))
        self.assertTrue(self.broken(lambda d: e(d).update(config={"dlnaContentType": "text/html"})))
        self.assertTrue(self.broken(lambda d: e(d).update(config={"defaultDelayMs": 5000})))

    def test_more_than_the_limit(self):
        def many(d):
            d["speakers"] = [dict(d["speakers"][1], id="speaker-%d" % i) for i in range(lib.MAX_ENTRIES + 1)]
        self.assertTrue(self.broken(many))


class Helpers(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(lib.clean("a\x00b\x1b  c\n d", 20), "ab c d")
        self.assertEqual(lib.clean("x" * 50, 10), "x" * 10)
        self.assertEqual(lib.clean(None, 10), "")

    def test_best_match(self):
        doc = good()
        wiim = {"platform": "DLNA", "model": "WiiM Pro Plus"}
        self.assertEqual(lib.best_match(doc, wiim)["id"], "wiim-dlna-restart")
        self.assertIsNone(lib.best_match(doc, {"platform": "AirPlay2", "model": "WiiM Pro Plus"}))
        self.assertIsNone(lib.best_match(doc, {"platform": "DLNA", "model": "nothing"}))
        self.assertIsNone(lib.best_match(doc, {"platform": "DLNA"}))


if __name__ == "__main__":
    unittest.main()
