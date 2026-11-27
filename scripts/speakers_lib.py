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
# Only things that are speakers: AriaCast receivers, Snapcast, VBAN and Sendspin are software on a
# phone, a computer or a server, so there is no speaker to judge and they are not offered.
PLATFORMS = {
    "AirPlay 2": "AirPlay2",
    "AirPlay 1": "AirPlay",
    "DLNA": "DLNA",
    "Google Cast": "Google Cast",
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


def haystack(device):
    """What an entry's words are looked for in: the name, model and maker of a device, lowercased.

    A device is a dict with optional "platform", "name", "model" and "manufacturer". This is the
    same rule the apps apply (tests/data/matching-cases.json holds the cases both must agree on).
    """
    return " ".join(device[k] for k in ("name", "model", "manufacturer") if device.get(k)).lower()


def specificity(entry, device):
    """How well an entry fits a device, or 0 if it does not fit.

    An entry that names a protocol only fits devices that speak it; one that does not fits any.
    A word found in the device's name or model scores its length, so "wiim pro" beats "wiim". A
    word found only in the maker's name scores 1: knowing the maker is better than nothing, but a
    model word is always more specific than a maker's.
    """
    platform = entry["match"].get("platform")
    if platform and platform != device.get("platform"):
        return 0
    words = entry["match"].get("mentions", [])
    own = " ".join(device[k] for k in ("name", "model") if device.get(k)).lower()
    best = max((len(w) for w in words if w in own), default=0)
    if best:
        return best
    return 1 if any(w in (device.get("manufacturer") or "").lower() for w in words) else 0


def matching(doc, device):
    """Every entry that fits the device, in list order."""
    return [e for e in doc["speakers"] if specificity(e, device) > 0]


def best_match(doc, device):
    """The entry that fits the device best (the longest word wins, the first on a tie), if any."""
    best, best_score = None, 0
    for e in doc["speakers"]:
        score = specificity(e, device)
        if score > best_score:
            best, best_score = e, score
    return best


def dump(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
