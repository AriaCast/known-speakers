# Known speakers

How speakers behave with [AriaCast](https://github.com/AriaCast/AriaCast-app), what you see when
something is wrong, and what to do. The AriaCast app reads this list (Settings → Known speakers)
and keeps it up to date.

Only behavior somebody reported or a maintainer checked is listed; a speaker that is not here is
untested, not broken. A status follows the most reported one, so one report does not flip a speaker.
Entries marked 🔒 are curated by a maintainer: reports are counted but do not change them.

<!-- Generated from speakers.json (list version 2). Do not edit by hand: the bot and
     `python3 scripts/render_readme.py` keep it current. -->

## Supported

| Speaker | Protocol | If it goes wrong | What to do | Reports | Evidence |
|---|---|---|---|---|---|
| Sonos (tested on Play:5) 🔒 | AirPlay 2 | On 1.1.9 the AirPlay 2 stream did not play, while DLNA to the same speaker did. | Update. Until then, cast to it over DLNA. |  | [#48](https://github.com/AriaCast/AriaCast-app/issues/48), confirmed by the reporter after the hotfix |
| Sonos (tested on Play:5) 🔒 | DLNA |  |  |  | [#48](https://github.com/AriaCast/AriaCast-app/issues/48), reporter: DLNA was working |
| WiiM (tested on Pro Plus) 🔒 | DLNA | The track title changes but playback stays paused at 0:00 after every track change.<br>Pressing play in the WiiM app starts it again. | Update: AriaCast now sends Play after every track change. If it still stops, press play once in the WiiM app and report it. |  | [#50](https://github.com/AriaCast/AriaCast-app/issues/50), fixed in the 2.0 line; the reporter's confirmation is not recorded |
| shairport-sync 🔒 | AirPlay 1 |  |  |  | Maintainer's own test in [#48](https://github.com/AriaCast/AriaCast-app/issues/48); the AirPlay version is not stated there, so it is listed under AirPlay 1 |
| iMac (iMac20,1) | AirPlay 2 |  |  | 1 supported | [#2](https://github.com/AriaCast/known-speakers/issues/2), reported by a user |

## Supported with quirks

| Speaker | Protocol | If it goes wrong | What to do | Reports | Evidence |
|---|---|---|---|---|---|
| shairport-sync 🔒 | AirPlay 2 | The speaker accepts the connection but timing is off, or AriaCast drops to AirPlay 1. | Nothing to do: AriaCast tries NTP timing and falls back to AirPlay 1 on its own. Real PTP needs root. |  | Code: PtpMaster (shairport-sync with nqptp accepts only PTP timing) |
| Apple TV 🔒 | AirPlay (video) | On Apple TVs that require pairing, casting a video fails with "This AirPlay device requires pairing for video". Audio casting is not affected. | Cast audio only. Video works with Apple TVs that allow unpaired access. |  | Roadmap status table and VideoTargets.kt |

## Unsupported

| Speaker | Protocol | If it goes wrong | What to do | Reports | Evidence |
|---|---|---|---|---|---|
| Amazon Echo Show 5 (1st gen), Echo Hub 🔒 | No local protocol | The speaker does not appear in AriaCast, and it has no AirPlay. | Bluetooth is the only local way in, and AriaCast does not send to Bluetooth speakers yet. |  | Maintainer's own devices; Alexa has no local streaming protocol |

## Add or confirm a speaker

In the app, answer the question that appears the first time you cast to a new speaker, or
long-press a speaker and choose **Report speaker**. It opens a pre-filled
[report](../../issues/new?template=speaker-report.yml). If the speaker is already here, your report
is counted; if not, it is added. See [docs/SCHEMA.md](docs/SCHEMA.md) for the file's format.
