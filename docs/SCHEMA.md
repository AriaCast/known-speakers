# The format of speakers.json

The AriaCast app downloads this file and lets it change what the app does, so it follows fixed rules.
The app checks the same rules when it loads the file: a file that breaks the top-level rules is
refused whole, and an entry that breaks its own is skipped, so a mistake here costs one entry, not
the list. `scripts/speakers_lib.py` is the checker used here (`python3 scripts/validate.py`).

```json
{
  "schema": 2,
  "version": 12,
  "updated": "2026-11-27",
  "speakers": [ { ...entry... } ]
}
```

`version` goes up by one on every change; an app only takes a list with a higher version than the
one it has. Up to 500 entries, 256 KB.

## An entry

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `a-z`, `0-9`, `-`, 3 to 64 characters, unique |
| `speaker` | yes | Brand and, where known, the model it was seen on (up to 80 characters) |
| `protocol` | yes | `AirPlay 2`, `AirPlay 1`, `DLNA`, `Google Cast`, … or `No local protocol` |
| `status` | yes | `supported`, `quirks` (supported with quirks) or `unsupported` |
| `match` | yes | `platform` (the app's protocol name; leave out to match any) and `mentions`: 1 to 8 lowercase words of 3 to 40 characters looked for in the speaker's name, model and maker. An entry with no words is rejected, so it cannot apply to every speaker |
| `symptoms` | for `quirks` and `unsupported` | What the user sees when it goes wrong |
| `whatToDo`, `since` | no | What to do; the first version where this holds |
| `evidence` | yes | Where this comes from |
| `reports` | no | How many reports were counted per status: `{"supported": 3, "quirks": 1}` |
| `locked` | no | `true` for entries a maintainer curated: reports are counted but never change the status |
| `notes` | no | The message the connection doctor shows, by two-letter language (`en`, `it`) |
| `config` | no | What this speaker needs that differs from the usual. Maintainers only: the bot never writes it |

## `config`

Only these, within these limits (anything else is dropped by the app):

| Knob | Values | Effect |
|---|---|---|
| `dlnaPlayAfterSetUri` | `true`/`false` | DLNA: send Play after each track change (the default is on) |
| `dlnaContentType` | `audio/wav`, `audio/x-wav` | DLNA: content type of the stream |
| `dlnaSkipInitialStop` | `true`/`false` | DLNA: skip the Stop sent before the stream address |
| `defaultDelayMs` | 0 to 2000 | Starting delay until the user sets their own |
| `sendMetadata` | `true`/`false` | Send titles and artwork to this speaker |

## Which entry a device belongs to

The apps and the bot use the same rule (`tests/data/matching-cases.json` holds the cases, and the app's
tests run the same file):

- An entry **fits** a device when its `match.platform` is absent or equal to the device's protocol, and
  one of its `mentions` is found (as lowercase text) in the device's name, model or maker.
- When several entries fit, the one with the **longest word found in the name or model** is the best
  (`wiim pro` beats `wiim`); a word found only in the maker's name counts 1, so a model word always beats
  a maker's. On a tie, the first in the list wins.

## What the bot does

A report is a form (`.github/ISSUE_TEMPLATE/speaker-report.yml`). The device is taken from the app's
"Speaker:" line (maker, model), or from what the reporter typed in *Speaker* when the device does not
say its model. **The name its owner gave a device is never its identity**: a report whose *Speaker* only
repeats that name is refused and asked for a brand and model.

- If the device fits an entry, the report is added to its `reports`, and the shown `status` becomes the
  most reported one (a tie keeps the current one). A `locked` entry never changes; if a report disagrees
  with a locked entry, the issue is left open with the `needs-review` label for a maintainer.
- If it fits nothing, a new entry is added with the status and symptoms the reporter wrote, recognised by
  the model.

The log in the issue is never stored, a person can send three reports a day, and `config` is never
written from a report. Only things that are speakers are offered in the form: AriaCast receivers,
Snapcast, VBAN and Sendspin are software on a phone, a computer or a server.

## Keeping the app and this repository in step

`tests/data/generated-sample.json` is what the bot writes for `tests/data/issue-new.md`, and
`tests/data/matching-cases.json` holds the matching cases. Both live in the app's tests too, which check
that the app accepts the first without skipping anything and gives the same answers on the second. If the
rules change, change `speakers_lib.py`, regenerate that file (`UPDATE_GOLDEN=1`, see the tests) and
copy it to the app.
