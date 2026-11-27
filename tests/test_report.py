import os
import unittest

from helpers import DATA, Run, form, lib, read, report


class ParseForm(unittest.TestCase):
    def test_cuts_the_form_into_fields(self):
        fields = report.parse_form(read("issue-new.md"))
        self.assertEqual(fields["Speaker"], "Acme Play 3")
        self.assertEqual(fields["How does it work?"], "Supported with quirks")
        self.assertIn("Needs a manual play", fields["What happens"])

    def test_edge_cases(self):
        self.assertEqual(report.parse_form("### Speaker\n\n_No response_\n")["Speaker"], "")
        self.assertEqual(report.parse_form("### Speaker\r\n\r\nX\r\n")["Speaker"], "X")
        self.assertEqual(report.parse_form(""), {})
        self.assertEqual(report.parse_form(None), {})


class NewSpeaker(unittest.TestCase):
    def test_it_is_added_and_matches_the_golden_file(self):
        r = Run(read("issue-new.md"))
        self.assertEqual(r.result(), "added")
        golden = os.path.join(DATA, "generated-sample.json")
        if os.environ.get("UPDATE_GOLDEN") == "1":
            with open(golden, "w", encoding="utf-8") as f:
                f.write(r.text())
        # The app's tests parse this same file, so what the bot writes is what the app accepts.
        self.assertEqual(r.text(), read("generated-sample.json"))

    def test_the_entry(self):
        r = Run(read("issue-new.md"))
        e = r.entry("acme-play-3-dlna")
        self.assertEqual(e["status"], "quirks")
        self.assertEqual(e["match"], {"platform": "DLNA", "mentions": ["play 3 pro"]})
        self.assertEqual(e["symptoms"], ["Stops after the first track", "Needs a manual play in the Acme app"])
        self.assertEqual(e["reports"], {"quirks": 1})
        self.assertEqual(e["evidence"], "[#77](https://github.com/AriaCast/known-speakers/issues/77), reported by a user")
        self.assertNotIn("locked", e)
        self.assertEqual(r.doc()["version"], 5)
        self.assertEqual(r.doc()["updated"], "2026-11-27")

    def test_the_readme_is_rewritten_with_it(self):
        self.assertIn("Acme Play 3", Run(read("issue-new.md")).readme())

    def test_the_log_is_never_stored(self):
        r = Run(read("issue-new.md"))
        self.assertNotIn("THE-LOG-MARKER", r.text())
        self.assertNotIn("THE-LOG-MARKER", r.readme())

    def test_existing_entries_are_untouched(self):
        self.assertEqual(Run(read("issue-new.md")).doc()["speakers"][:2], lib.load(os.path.join(DATA, "base.json"))["speakers"])

    def test_the_same_name_over_another_protocol_is_a_new_speaker(self):
        r = Run(form(speaker="WiiM", protocol="AirPlay 2"))
        self.assertEqual(r.result(), "added")
        self.assertEqual(r.entry("wiim-airplay-2")["match"]["platform"], "AirPlay2")

    def test_no_protocol_means_nothing_to_match_it_on(self):
        r = Run(form(speaker="Amazon Echo Show 5", protocol="No local protocol", status="Unsupported", happens="Not found"))
        self.assertEqual(r.entry("amazon-echo-show-5-no-local-protocol")["match"], {"mentions": ["amazon echo show 5"]})

    def test_a_working_speaker_needs_no_symptoms(self):
        r = Run(form(speaker="Fresh Speaker", status="Supported", happens=""))
        self.assertEqual(r.result(), "added")
        self.assertNotIn("symptoms", r.entry("fresh-speaker-dlna"))

    def test_the_comment_says_what_happened(self):
        self.assertIn("added it as **Supported with quirks**", Run(read("issue-new.md")).said())


class SameSpeakerAsTheList(unittest.TestCase):
    """What the app really sends, against entries that use broad words, as the curated ones do."""

    def app_report(self, line, protocol="DLNA", status="Supported", speaker=None, happens=""):
        return form(speaker=speaker or "x", protocol=protocol, status=status, happens=happens,
                    details="App: AriaCast 2.0.0\nSpeaker: " + line + "\nCast: CASTING")

    def test_a_model_containing_the_entrys_word_counts_into_the_entry(self):
        r = Run(self.app_report("protocol=DLNA, manufacturer=Linkplay, model=WiiM Pro Plus, name=Den", speaker="Linkplay WiiM Pro Plus"), base="curated.json")
        self.assertEqual(r.result(), "counted")
        self.assertEqual(len(r.doc()["speakers"]), len(lib.load(os.path.join(DATA, "curated.json"))["speakers"]))
        self.assertEqual(r.entry("wiim-dlna-restart")["reports"], {"supported": 1})

    def test_the_makers_name_is_enough(self):
        r = Run(self.app_report("protocol=DLNA, manufacturer=Linkplay Technology Inc., model=Pro Plus, name=Den", speaker="Linkplay Pro Plus"), base="curated.json")
        self.assertEqual(r.result(), "counted")

    def test_the_most_specific_entry_gets_the_report(self):
        r = Run(self.app_report("protocol=DLNA, manufacturer=Linkplay, model=WiiM Pro Plus, name=Den", speaker="x"), base="curated-two.json")
        self.assertEqual(r.entry("wiim-pro")["reports"], {"supported": 1})
        self.assertEqual(r.entry("wiim-dlna-restart")["reports"], {})

    def test_a_name_given_at_home_is_not_an_identity(self):
        r = Run(self.app_report("protocol=AirPlay2, name=Studio", protocol="AirPlay 2", speaker="Studio"), base="curated.json")
        self.assertEqual(r.result(), "refused")
        self.assertIn("brand and model", r.said())
        self.assertTrue(r.untouched())

    def test_the_same_name_is_fine_once_the_reporter_writes_the_model(self):
        r = Run(self.app_report("protocol=AirPlay2, name=Studio", protocol="AirPlay 2", speaker="Acme Hi-Fi One"), base="curated.json")
        self.assertEqual(r.result(), "added")
        self.assertEqual(r.entry("acme-hi-fi-one-airplay-2")["match"]["mentions"], ["acme hi-fi one"])

    def test_two_owners_of_the_same_unlisted_model_end_up_on_one_entry(self):
        line = "protocol=DLNA, manufacturer=Acme, model=Play 3 Pro, name=%s"
        first = Run(self.app_report(line % "Den", speaker="Acme Play 3 Pro"), base="curated.json")
        self.assertEqual(first.result(), "added")
        self.assertEqual(first.entry("acme-play-3-pro-dlna")["match"]["mentions"], ["play 3 pro"])
        # Another owner, with a name of their own, on a list that now has the first report in it.
        second = Run(self.app_report(line % "Kitchen", speaker="Acme Play 3 Pro"), base="curated-acme.json")
        self.assertEqual(second.result(), "counted")
        self.assertEqual(second.entry("acme-play-3-pro-dlna")["reports"], {"supported": 2})
        self.assertEqual(len(second.doc()["speakers"]), len(lib.load(os.path.join(DATA, "curated-acme.json"))["speakers"]))

    def test_an_echo_from_a_scan_counts_into_the_curated_echo_entry(self):
        r = Run(form(speaker="Amazon Echo Show 5", protocol="No local protocol", status="Unsupported", happens="not found",
                     details="Speaker: name=Echo Show 5-3f2"), base="curated.json")
        self.assertEqual(r.result(), "counted")  # it agrees with the entry, so no review
        self.assertEqual(r.entry("echo-show5-hub-no-airplay")["reports"], {"unsupported": 1})

    def test_a_report_that_disagrees_with_a_checked_entry_asks_for_review(self):
        r = Run(self.app_report("protocol=DLNA, manufacturer=Linkplay, model=WiiM Pro Plus, name=Den", status="Unsupported", speaker="x", happens="Never plays"), base="curated.json")
        self.assertEqual(r.result(), "counted-review")
        self.assertEqual(r.entry("wiim-dlna-restart")["status"], "supported")
        self.assertEqual(r.entry("wiim-dlna-restart")["reports"], {"unsupported": 1})
        self.assertIn("left this issue open", r.said())

    def test_a_report_that_agrees_with_a_checked_entry_just_counts(self):
        r = Run(self.app_report("protocol=DLNA, manufacturer=Linkplay, model=WiiM Pro Plus, name=Den", speaker="x"), base="curated.json")
        self.assertEqual(r.result(), "counted")

    def test_software_receivers_are_not_speakers(self):
        for protocol in ("AriaCast", "VBAN", "Snapcast", "Sendspin"):
            r = Run(form(speaker="Anything Box", protocol=protocol, status="Supported", happens=""))
            self.assertEqual(r.result(), "refused", protocol)
            self.assertIn("Protocol", r.said())


class KnownSpeaker(unittest.TestCase):
    def test_a_report_is_counted_not_added(self):
        r = Run(form(speaker="Open Box", status="Supported", happens=""))
        self.assertEqual(r.result(), "counted")
        self.assertEqual(len(r.doc()["speakers"]), 2)
        self.assertEqual(r.entry("open-box-dlna")["reports"], {"supported": 2})
        self.assertIn("already listed as `open-box-dlna`", r.said())

    def test_the_model_the_app_reports_finds_the_entry_too(self):
        details = "Speaker: protocol=DLNA, manufacturer=Open, model=Open Box, name=Den"
        r = Run(form(speaker="Something else typed", details=details, status="Supported", happens=""))
        self.assertEqual(r.result(), "counted")

    def test_counting_needs_no_symptoms(self):
        self.assertEqual(Run(form(speaker="Open Box", status="Unsupported", happens="")).result(), "counted")

    def test_one_report_cannot_flip_a_speaker(self):
        r = Run(form(speaker="Open Box", status="Unsupported", happens=""))
        self.assertEqual(r.entry("open-box-dlna")["reports"], {"supported": 1, "unsupported": 1})
        self.assertEqual(r.entry("open-box-dlna")["status"], "supported")  # a tie keeps what it was

    def test_the_most_reported_status_wins_when_the_report_says_what_happens(self):
        r = Run(form(speaker="Open Box", status="Unsupported", happens="Never plays"), base="open-box-tied.json")
        e = r.entry("open-box-dlna")
        self.assertEqual(e["reports"], {"supported": 1, "unsupported": 2})
        self.assertEqual(e["status"], "unsupported")
        self.assertEqual(e["symptoms"], ["Never plays"])
        self.assertEqual(lib.validate(r.doc()), [])

    def test_without_symptoms_the_count_goes_up_but_the_status_waits(self):
        r = Run(form(speaker="Open Box", status="Unsupported", happens=""), base="open-box-tied.json")
        e = r.entry("open-box-dlna")
        self.assertEqual(e["reports"], {"supported": 1, "unsupported": 2})
        self.assertEqual(e["status"], "supported")
        self.assertNotIn("symptoms", e)
        self.assertEqual(lib.validate(r.doc()), [])

    def test_existing_symptoms_are_kept_not_replaced(self):
        r = Run(form(speaker="Open Box", status="Unsupported", happens="Something else"), base="open-box-tied-with-symptoms.json")
        self.assertEqual(r.entry("open-box-dlna")["symptoms"], ["Original"])
        self.assertEqual(r.entry("open-box-dlna")["status"], "unsupported")

    def test_a_locked_entry_counts_reports_but_never_changes(self):
        # The report explains itself, so without "locked" the status would flip.
        r = Run(form(speaker="WiiM", status="Unsupported", happens="Never plays"), base="wiim-many-reports.json")
        e = r.entry("wiim-dlna-restart")
        self.assertEqual(e["status"], "supported")
        self.assertEqual(e["reports"]["unsupported"], 6)
        self.assertNotIn("symptoms", e)
        self.assertIn("curated by a maintainer", r.said())

    def test_the_version_still_goes_up_when_a_report_is_counted(self):
        self.assertEqual(Run(form(speaker="Open Box", status="Supported", happens="")).doc()["version"], 5)


class Refusals(unittest.TestCase):
    def assertRefused(self, body, words, **kwargs):
        r = Run(body, **kwargs)
        self.assertEqual(r.result(), "refused")
        self.assertTrue(r.untouched(), "a refused report must not touch the list")
        self.assertIn(words, r.said())

    def test_no_speaker(self):
        self.assertRefused(form(speaker=""), "Speaker")

    def test_a_protocol_the_form_does_not_offer(self):
        self.assertRefused(form(protocol="Telepathy"), "Protocol")

    def test_a_status_the_form_does_not_offer(self):
        self.assertRefused(form(status="Great"), "How does it work")

    def test_a_new_speaker_that_does_not_work_must_say_how(self):
        self.assertRefused(form(status="Unsupported", happens=""), "What happens")

    def test_names_too_short_or_made_of_punctuation(self):
        self.assertRefused(form(speaker="TV"), "too short")
        self.assertRefused(form(speaker="!!! ???"), "too short")

    def test_an_empty_issue(self):
        self.assertRefused("", "Speaker")

    def test_three_reports_a_day_are_allowed_and_a_fourth_is_not(self):
        self.assertEqual(Run(read("issue-new.md"), today=3).result(), "added")
        self.assertRefused(read("issue-new.md"), "limit", today=4)


class Hostile(unittest.TestCase):
    def test_quotes_backslashes_and_markup_stay_data(self):
        r = Run(form(speaker='Evil "speaker" \\ <script>', happens='x"}], "status": "supported", "y": [{"z'))
        self.assertEqual(lib.validate(r.doc()), [])
        self.assertEqual(r.doc()["speakers"][-1]["status"], "quirks")

    def test_control_characters_are_removed(self):
        e = Run(form(speaker="Acme\x00 Play\x1b[31m 3", happens="a\x07b")).doc()["speakers"][-1]
        self.assertNotRegex(e["speaker"], r"[\x00-\x1f]")
        self.assertEqual(e["symptoms"], ["ab"])

    def test_lengths_are_capped(self):
        r = Run(form(speaker="S" * 500, happens="\n".join("line %d %s" % (i, "y" * 500) for i in range(40))))
        e = r.doc()["speakers"][-1]
        self.assertLessEqual(len(e["speaker"]), 80)
        self.assertLessEqual(len(e["symptoms"]), 8)
        self.assertTrue(all(len(s) <= 240 for s in e["symptoms"]))
        self.assertEqual(lib.validate(r.doc()), [])

    def test_config_can_never_come_from_a_report(self):
        for body in (form(happens='x\n### config\n\n{"sendMetadata": false}'), form(speaker="Open Box", status="Supported", happens="")):
            doc = Run(body).doc()
            self.assertTrue(all("config" not in e for e in doc["speakers"]))
            self.assertEqual(lib.validate(doc), [])

    def test_whatever_is_written_the_list_stays_valid(self):
        for name in ("Acme Play 3", "Acme  play 3", "ACME PLAY 3!", "日本語スピーカー", "a" * 90):
            self.assertEqual(lib.validate(Run(form(speaker=name)).doc()), [], name)

    def test_ids_never_collide(self):
        r = Run(form(speaker="Open Box", protocol="DLNA", status="Supported", happens=""))  # counted, no new id
        self.assertEqual(len({e["id"] for e in r.doc()["speakers"]}), 2)

    def test_an_odd_repository_name_stops_the_run(self):
        with self.assertRaises(SystemExit):
            Run(read("issue-new.md"), repo="a/b; rm -rf /")

    def test_a_non_numeric_issue_number_stops_the_run(self):
        with self.assertRaises(ValueError):
            Run(read("issue-new.md"), number="1; echo")


class ShownStatus(unittest.TestCase):
    def test_rules(self):
        s = report.shown_status
        self.assertEqual(s({"status": "supported", "reports": {}}), "supported")
        self.assertEqual(s({"status": "supported", "reports": {"unsupported": 1, "supported": 1}}), "supported")
        self.assertEqual(s({"status": "supported", "reports": {"unsupported": 2, "supported": 1}}), "unsupported")
        self.assertEqual(s({"status": "quirks", "reports": {"supported": 2, "unsupported": 2}}), "supported")  # tie, current not among them
        self.assertEqual(s({"status": "unsupported", "reports": {"supported": 2, "unsupported": 2}}), "unsupported")


if __name__ == "__main__":
    unittest.main()
