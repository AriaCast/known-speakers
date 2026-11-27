"""The list of known speakers: what the file may contain, and how it is read and written.

The apps read speakers.json and let it change what they do, so these rules are the contract.
The app applies the same rules when it loads the file and drops what breaks them; keeping both
sides in step is what tests/data/ is for (see docs/SCHEMA.md).
"""
import json
import re

SCHEMA = 2
MAX_BYTES = 256 * 1024
MAX_ENTRIES = 500
MAX_REPORTS = 1_000_000

STATUSES = ("supported", "quirks", "unsupported")
STATUS_LABELS = {"supported": "Supported", "quirks": "Supported with quirks", "unsupported": "Unsupported"}

# Protocol name in the report form -> the platform name the apps use (None: no protocol to match).
PLATFORMS = {
    "AirPlay 2": "AirPlay2",
    "AirPlay 1": "AirPlay",
    "DLNA": "DLNA",
    "Google Cast": "Google Cast",
    "Snapcast": "Snapcast",
    "Sendspin": "Sendspin",
    "AriaCast": "AriaCast",
    "VBAN": "VBAN",
    "No local protocol": None,
    "Other": None,
}

ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{2,63}")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
DLNA_CONTENT_TYPES = ("audio/wav", "audio/x-wav")
CONFIG_KNOBS = ("dlnaPlayAfterSetUri", "dlnaContentType", "dlnaSkipInitialStop", "defaultDelayMs", "sendMetadata")


def clean(text, limit):
    """One line of plain text: control characters out, whitespace collapsed, cut to `limit`."""
    text = CONTROL.sub("", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def mention_ok(word):
    """A word an entry is recognised by: lowercase, 3 to 40 characters, with real letters or digits."""
    return word == word.lower() and 3 <= len(word) <= 40 and len(re.sub(r"[^a-z0-9]", "", word)) >= 3


def validate(doc):
    """Every way `doc` breaks the rules, as a list of sentences (empty when it is good)."""
    problems = []
    if not isinstance(doc, dict):
        return ["the file is not an object"]
    if doc.get("schema") != SCHEMA:
        problems.append("schema must be %d" % SCHEMA)
    if not isinstance(doc.get("version"), int) or doc["version"] < 0:
        problems.append("version must be a whole number, 0 or more")
    speakers = doc.get("speakers")
    if not isinstance(speakers, list):
        return problems + ["speakers must be a list"]
    if len(speakers) > MAX_ENTRIES:
        problems.append("more than %d entries" % MAX_ENTRIES)
    seen = set()
    for i, e in enumerate(speakers):
        name = e.get("id", "#%d" % i) if isinstance(e, dict) else "#%d" % i
        if not isinstance(e, dict):
            problems.append("%s: not an object" % name)
            continue
        def bad(why):
            problems.append("%s: %s" % (name, why))
        if not isinstance(e.get("id"), str) or not ID_PATTERN.fullmatch(e["id"]):
            bad("bad id")
        elif e["id"] in seen:
            bad("duplicate id")
        else:
            seen.add(e["id"])
        for field in ("speaker", "protocol", "evidence"):
            if not isinstance(e.get(field), str) or not e[field].strip():
                bad("%s is empty" % field)
        if e.get("status") not in STATUSES:
            bad("status must be one of %s" % ", ".join(STATUSES))
        match = e.get("match")
        words = match.get("mentions") if isinstance(match, dict) else None
        if not isinstance(words, list) or not words or not all(isinstance(w, str) and mention_ok(w) for w in words):
            bad("needs at least one word to match, lowercase, 3 to 40 characters")
        symptoms = e.get("symptoms", [])
        if not isinstance(symptoms, list) or not all(isinstance(s, str) for s in symptoms):
            bad("symptoms must be a list of text")
        elif e.get("status") in ("quirks", "unsupported") and not symptoms:
            bad("an entry that does not simply work must say what happens")
        reports = e.get("reports", {})
        if not isinstance(reports, dict) or any(
            k not in STATUSES or not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= MAX_REPORTS for k, v in reports.items()
        ):
            bad("reports must count supported, quirks and unsupported with whole numbers")
        config = e.get("config")
        if config is not None:
            if not isinstance(config, dict) or any(k not in CONFIG_KNOBS for k in config):
                bad("config may only use: %s" % ", ".join(CONFIG_KNOBS))
            elif "dlnaContentType" in config and config["dlnaContentType"] not in DLNA_CONTENT_TYPES:
                bad("dlnaContentType must be one of %s" % ", ".join(DLNA_CONTENT_TYPES))
            elif "defaultDelayMs" in config and not (isinstance(config["defaultDelayMs"], int) and 0 <= config["defaultDelayMs"] <= 2000):
                bad("defaultDelayMs must be 0 to 2000")
    return problems


def find(doc, platform, mention):
    """The entry for the same speaker over the same protocol, if the list has one."""
    for e in doc["speakers"]:
        if mention in e["match"].get("mentions", []) and e["match"].get("platform") == platform:
            return e
    return None


def dump(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
