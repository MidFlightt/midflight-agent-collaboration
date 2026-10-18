# Midflight video handoff

The editable 3:42 pitch lives here. Start with the native Remotion project;
`presentation/Midflight-animated.html` is the self-contained presentation reference.
The video does not capture or play that HTML file.

## Demo files — keep both takes

| Recording | File | Use |
|---|---|---|
| **Primary demo — full original** | [Demo.mov](recordings/Demo.mov) | Most important source; preserved in full for further editing (about 65 seconds). |
| Primary demo — trimmed version | [live-agent-demo.mp4](public/demo/live-agent-demo.mp4) | 52-second cut already used in the 3:42 product video. |
| Second take — separate footage | [agent-interface-demo-take-2.mp4](recordings/agent-interface-demo-take-2.mp4) | 58-second alternate take for teammates; not in the product video. |

Both takes are retained. `Demo.mov` matches the first recording used for the
primary trimmed clip. Adding its full source does not change the product video,
the selected demo, or the timeline.

## Run

Use Node.js 22+ and npm. From this directory:

```sh
npm ci
npm run studio
```

Choose **MidflightPitch** for the full cut or **Opening** for the 47-second opening.

```sh
npm run typecheck
npm run render
npm run render:opening
```

Exports go into ignored `out/`. Remotion may download its browser on first render.

## What to edit

| Work | File |
|---|---|
| Overall sequence, section lengths, demo slot | `src/combined-story/Pitch.tsx` |
| Opening order and curved agent-chip handoff | `src/combined-story/ReorderedOpening.tsx` |
| Team lead and single failed bridge merge | `src/lead-intro/LeadIntro.tsx` |
| Project/task delegation and flight chapter | `src/merged-story/MergedStory.tsx` |
| Planes, check-ins, agent labels and team expansion | `src/flight3d/FlightFilm.tsx` |
| Benchmark setup and results | `src/combined-story/BenchmarkSetup.tsx` |
| Three selected flowcharts | `public/flowcharts/` |
| Research still and soundtrack | `public/research/`, `public/audio/` |
| HTML presentation reference | `presentation/Midflight-animated.html` |

The workflow and architecture charts include editable SVGs plus their PNG renders.
The selective-update chart is supplied as a PNG. These are the latest selected
source files from the shared workspace, including the updated architecture chart.
When editing SVGs, update the matching PNG: the video renders the PNGs.

## Current sequence

1920 × 1080, 30 fps, 6,660 frames, exactly 3:42.

| Time | Section |
|---|---|
| 0:00–0:47 | Project delegation → team lead → direct chip-to-plane handoff → flight and team |
| 0:47–1:39 | Live coding demo |
| 1:39–1:59 | How Midflight works |
| 1:59–2:24 | How Midflight shares changes |
| 2:24–2:44 | System architecture |
| 2:44–3:09 | Benchmark setup |
| 3:09–3:24 | Benchmark results |
| 3:24–3:37 | Context research |
| 3:37–3:42 | Thank you |

The opening uses the original native animations. It shows one merge attempt, then
fades the lead scene while Agent A/B chips move directly onto their plane labels.
There is no second merge attempt or return to the project diagram in that handoff.
The charts and research still retain their reading time. The closing slogan and
failure-path section are omitted.

## Demo recording

The demo is included at `public/demo/live-agent-demo.mp4` and plays by default.
It is the continuous 0:11–1:03 interval (52 seconds) from
`Screen Recording 2026-10-17 at 19.26.18.mov`. Initial setup/idle time and the
recording-control overlay at the end are removed. The macOS menu strip and terminal
status strip are cropped; all four agent panes remain visible. The clip is fitted
to 1080p at 30 fps without stretching, retains the original quiet audio with brief
edge fades, and plays at its original speed. It shows live work in progress, including agent check-ins, interface updates,
and component test results.

The full primary source is preserved at `recordings/Demo.mov`; the trimmed clip
remains selected by default. To use a replacement, put it at `public/demo.mp4`
and render:

```sh
npm run render -- --props='{"demoFile":"demo.mp4"}'
```

Use a 52-second replacement or update `DEMO_SECONDS` and this timeline. Longer
footage is trimmed to the scene. The included demo runs from 0:47 to 1:39 in the pitch.

Current source, required assets, both demo takes, and the full primary
`Demo.mov` are tracked here. Installations, exports, review screenshots, old cuts,
alternative diagrams, and other raw recordings stay out of Git. The HTML reference embeds its own media and can be
opened offline.

## Extra footage for teammates

[Agent interface demo — take 2](recordings/agent-interface-demo-take-2.mp4) is a
standalone 58-second clip from `Screen Recording 2026-10-17 at 21.01.13.mov`,
trimmed to 0:12–1:10. Browser/fullscreen setup and ending recording controls are
excluded; the macOS menu/status strips are cropped. All four panes, original speed,
and audio are retained, at 1080p/30 fps.

This extra take is outside `public/` and is not referenced by Remotion. The
3:42 product video and its existing demo clip are unchanged.
