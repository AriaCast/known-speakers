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

## What the bot does

A report is a form (`.github/ISSUE_TEMPLATE/speaker-report.yml`). If the speaker (same protocol and
a word in `mentions`) is already listed, the report is added to `reports` and the shown `status`
becomes the most reported one (a tie keeps the current one; `locked` entries never change). If not,
a new entry is added with the status and symptoms the reporter wrote. The log in the issue is never
stored, a person can send three reports a day, and `config` is never written from a report.

The bot also accepts the compact report posted by the AriaCast app. It records it as `supported`
only when the report says `Cast: CASTING` and its log contains a successful streaming event;
otherwise it asks for a manual report so an uncertain result is not added to the list.

The workflow runs when a `Speaker:` issue is opened or reopened. If an existing report did not
trigger, add the `speaker-report` label or comment `/process` on that issue. A hidden marker in
the bot's reply prevents the same issue from being counted twice.

## Keeping the app and this repository in step

`tests/data/generated-sample.json` is what the bot writes for `tests/data/issue-new.md`. The same
file lives in the app's tests, which check that the app accepts it without skipping anything. If the
rules change, change `speakers_lib.py`, regenerate that file (`UPDATE_GOLDEN=1`, see the tests) and
copy it to the app.
