# Midflight video handoff

The editable 3:30 pitch lives here. Start with the native Remotion project;
`presentation/Midflight-animated.html` is the self-contained presentation reference.
The video does not capture or play that HTML file.

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

1920 × 1080, 30 fps, 6,300 frames, exactly 3:30.

| Time | Section |
|---|---|
| 0:00–0:47 | Project delegation → team lead → direct chip-to-plane handoff → flight and team |
| 0:47–1:27 | Demo placeholder |
| 1:27–1:47 | How Midflight works |
| 1:47–2:12 | How Midflight shares changes |
| 2:12–2:32 | System architecture |
| 2:32–2:57 | Benchmark setup |
| 2:57–3:12 | Benchmark results |
| 3:12–3:25 | Context research |
| 3:25–3:30 | Thank you |

The opening uses the original native animations. It shows one merge attempt, then
fades the lead scene while Agent A/B chips move directly onto their plane labels.
There is no second merge attempt or return to the project diagram in that handoff.
The charts and research still retain their reading time. The closing slogan and
failure-path section are omitted.

## Insert the demo

The 40-second slot is intentionally still a placeholder. Put a 40-second recording
at `public/demo.mp4`, then render:

```sh
npm run render -- --props='{"demoFile":"demo.mp4"}'
```

The recording should cover the full slot; longer footage is trimmed. If its final
length changes, update `PITCH_CHAPTERS` and this timeline. Demo audio is included.

Only current source and required assets are tracked here. Installations, exports,
review screenshots, old cuts, alternative diagrams, and recording footage stay out
of Git. The HTML reference embeds its own media and can be opened offline.
