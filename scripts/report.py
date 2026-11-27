#!/usr/bin/env python3
"""Record a "Speaker report" issue in speakers.json.

Run by .github/workflows/report.yml. The rule is short:

  * the speaker is already in the list  ->  count the report under its status;
  * it is not                           ->  add it, with the status the reporter chose.

Nothing else is decided here. An entry's shown status follows the most reported one (a tie keeps
the current one), so a single report cannot flip a speaker, and an entry a maintainer marked
"locked" is counted but never changes. Settings ("config") can only be written by a maintainer,
never from a report, and the log in the issue is never stored.

The issue text is written by anyone, so it is only read as data: cut into fields, checked against
speakers_lib's rules, and written back by a JSON serializer.

    ISSUE_BODY, ISSUE_NUMBER, GITHUB_REPOSITORY, AUTHOR_REPORTS_TODAY   from the workflow
    python3 scripts/report.py speakers.json comment.md
"""
import datetime
import os
import re
import sys

import render_readme
import speakers_lib as lib

MAX_PER_AUTHOR_PER_DAY = 3
FORM_STATUS = {label: key for key, label in lib.STATUS_LABELS.items()}


def parse_form(body):
    """Cut a rendered issue form into {label: text}. GitHub writes each field as `### Label`."""
    fields, label, lines = {}, None, []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            if label is not None:
                fields[label] = "\n".join(lines).strip()
            label, lines = line[4:].strip(), []
        elif label is not None:
            lines.append(line)
    if label is not None:
        fields[label] = "\n".join(lines).strip()
    return {k: ("" if v == "_No response_" else v) for k, v in fields.items()}


def symptoms_of(fields):
    return [s for s in (lib.clean(l, 240) for l in fields.get("What happens", "").split("\n")) if s][:8]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def mention_for(fields, speaker):
    """The phrase a speaker is recognised by: the model the app reported, else what was typed."""
    found = re.search(r"model=(.*?)(?:, (?:name|manufacturer|protocol)=|$)", fields.get("Speaker details", ""), re.M)
    phrase = lib.clean(found.group(1) if found else speaker, 40).lower()
    return phrase if lib.mention_ok(phrase) else None


def shown_status(entry):
    """The most reported status; a tie keeps the current one, or the first of the tied."""
    counts = entry.get("reports", {})
    top = max((counts.get(s, 0) for s in lib.STATUSES), default=0)
    leaders = [s for s in lib.STATUSES if counts.get(s, 0) == top]
    return entry["status"] if entry["status"] in leaders or top == 0 else leaders[0]


def record(fields, number, repo, doc, reports_today=0):
    """Returns (outcome, entry, text): outcome is "added", "counted" or "refused"."""
    refuse = lambda why: ("refused", None, why)  # noqa: E731
    if reports_today > MAX_PER_AUTHOR_PER_DAY:
        return refuse("You have sent %d reports in the last day; the limit is %d. Please try again tomorrow." % (reports_today, MAX_PER_AUTHOR_PER_DAY))
    speaker = lib.clean(fields.get("Speaker", ""), 80)
    protocol = lib.clean(fields.get("Protocol", ""), 40)
    status = FORM_STATUS.get(lib.clean(fields.get("How does it work?", ""), 40))
    if not speaker:
        return refuse("The *Speaker* field is empty.")
    if protocol not in lib.PLATFORMS:
        return refuse("The *Protocol* is not one of the options in the form.")
    if status is None:
        return refuse("*How does it work?* is not one of the options in the form.")
    mention = mention_for(fields, speaker)
    if mention is None:
        return refuse("The speaker's name is too short to recognise it by.")
    platform = lib.PLATFORMS[protocol]

    existing = lib.find(doc, platform, mention)
    if existing is not None:
        reports = existing.setdefault("reports", {})
        reports[status] = min(reports.get(status, 0) + 1, lib.MAX_REPORTS)
        symptoms = symptoms_of(fields)
        if not existing.get("locked"):
            shown = shown_status(existing)
            if shown != "supported" and not existing.get("symptoms"):
                # A speaker shown as not simply working must say what happens (the list's rule).
                # Take it from this report; without it, keep the status until a report explains.
                if symptoms:
                    existing["symptoms"] = symptoms
                else:
                    shown = existing["status"]
            existing["status"] = shown
        return "counted", existing, ""

    symptoms = symptoms_of(fields)
    if status != "supported" and not symptoms:
        return refuse("Please describe what happens in *What happens*: a speaker that does not simply work needs its symptoms.")
    if len(doc["speakers"]) >= lib.MAX_ENTRIES:
        return refuse("The list is full.")
    base = slug("%s %s" % (speaker, protocol)) or "speaker"
    taken = {s["id"] for s in doc["speakers"]}
    entry_id, n = base, 2
    while entry_id in taken or not lib.ID_PATTERN.fullmatch(entry_id):
        entry_id = "%s-%d" % (base, n)
        n += 1
        if n > 99:
            return refuse("Could not make an id for this speaker.")
    entry = {
        "id": entry_id,
        "speaker": speaker,
        "protocol": protocol,
        "status": status,
        "match": {"platform": platform, "mentions": [mention]} if platform else {"mentions": [mention]},
    }
    if symptoms:
        entry["symptoms"] = symptoms
    entry["evidence"] = "[#%d](https://github.com/%s/issues/%d), reported by a user" % (number, repo, number)
    entry["reports"] = {status: 1}
    doc["speakers"].append(entry)
    return "added", entry, ""


def comment_for(outcome, entry, why):
    if outcome == "refused":
        return "Thanks for the report. I could not record it: %s\n\nPlease open a new report once that is fixed." % why
    label = lib.STATUS_LABELS[entry["status"]]
    if outcome == "added":
        return "Thanks. **%s** (%s) was not in the list, so I added it as **%s**. Apps pick it up within a day." % (entry["speaker"], entry["protocol"], label)
    counts = ", ".join("%d %s" % (entry["reports"].get(s, 0), lib.STATUS_LABELS[s].lower()) for s in lib.STATUSES if entry["reports"].get(s, 0))
    note = " This entry is curated by a maintainer, so reports are counted but do not change it." if entry.get("locked") else ""
    return "Thanks. **%s** (%s) is already listed as `%s`, so I counted your report. Reports so far: %s. Listed as **%s**.%s" % (
        entry["speaker"], entry["protocol"], entry["id"], counts, label, note)


def main(argv, env):
    data_path, comment_path = argv[1], argv[2]
    number = int(env["ISSUE_NUMBER"])
    repo = env["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo):
        raise SystemExit("unexpected repository name")
    doc = lib.load(data_path)
    outcome, entry, why = record(parse_form(env.get("ISSUE_BODY", "")), number, repo, doc, int(env.get("AUTHOR_REPORTS_TODAY") or 0))
    if outcome != "refused":
        doc["version"] = int(doc["version"]) + 1
        # SPEAKER_REPORT_TODAY only exists so the tests can pin the date.
        doc["updated"] = env.get("SPEAKER_REPORT_TODAY") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        problems = lib.validate(doc)
        if problems:  # never write a list the apps would reject
            raise SystemExit("the result would not be valid: " + "; ".join(problems))
        with open(data_path, "w", encoding="utf-8") as f:
            f.write(lib.dump(doc))
        readme = os.path.join(os.path.dirname(os.path.abspath(data_path)), "README.md")
        with open(readme, "w", encoding="utf-8") as f:
            f.write(render_readme.render(doc))
    with open(comment_path, "w", encoding="utf-8") as f:
        f.write(comment_for(outcome, entry, why) + "\n")
    out = env.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write("result=%s\n" % outcome)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv, os.environ))
