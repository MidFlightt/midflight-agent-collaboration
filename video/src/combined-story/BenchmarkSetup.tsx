import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {C} from '../flight3d/model';

// How the PigeonPost benchmark is built and run, then what it found, to talk over. Four
// moving beats, each building on the last: six agents on six laptops, the six surprises
// that arrive mid-build, the three ways to coordinate, and the merge with its twenty
// checks. Those show no result: the checks fill in one neutral colour. Then the results
// table, which fades in and stays. The facts are from docs/benchmark-pigeonpost.md and
// docs/benchmark-pigeonpost-markers.md in the midflight repo.

// How long each beat lasts. Change one and the beats after it move along.
const CASE_FRAMES = 120;
const SURPRISES_FRAMES = 150;
const WAYS_FRAMES = 150;
const SCORE_FRAMES = 180;
const TABLE_FRAMES = 240;

const SURPRISES_AT = CASE_FRAMES;
const WAYS_AT = SURPRISES_AT + SURPRISES_FRAMES;
const SCORE_AT = WAYS_AT + WAYS_FRAMES;
const TABLE_AT = SCORE_AT + SCORE_FRAMES;
export const BENCHMARK_SETUP_FRAMES = TABLE_AT + TABLE_FRAMES;

const CARD = '#101923';
const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ENTER = Easing.bezier(0.16, 1, 0.3, 1);
const TRAVEL = Easing.bezier(0.65, 0, 0.35, 1);

const PARTS = ['Roost', 'Pricing', 'Dispatch', 'Billing', 'Command line', 'Tracking'];
const LATE = 5; // tracking's agent joins late

// The row of laptops.
const TILE = 240;
const GAP = 30;
const ROW_X = (1920 - (6 * TILE + 5 * GAP)) / 2;
const ROW_W = 6 * TILE + 5 * GAP;
const ROW_Y = 400;
const tileX = (i: number) => ROW_X + i * (TILE + GAP);

// The six things that happen after the plan is written, in the order a trial meets them.
const SURPRISES = ['Opposite instructions', 'A note against the plan', 'kg → grams', 'Plan change', 'Late joiner', 'Nobody planned it'];
const LINE_Y = 740;
const LINE_FROM = SURPRISES_AT + 10;
const LINE_TO = SURPRISES_AT + SURPRISES_FRAMES - 18;
const surpriseX = (k: number) => ROW_X + ((k + 0.5) / SURPRISES.length) * ROW_W;
const surpriseAt = (k: number) => LINE_FROM + ((k + 0.5) / SURPRISES.length) * (LINE_TO - LINE_FROM);
const JOINS_AT = surpriseAt(4);

const fade = (frame: number, from: number, frames = 14) => interpolate(frame, [from, from + frames], [0, 1], CLAMP);
const rise = (frame: number, from: number, by = 24) =>
  `0px ${interpolate(frame, [from, from + 14], [by, 0], {...CLAMP, easing: ENTER})}px`;

// The line under the kicker. Each beat has one; the last one stays.
const Caption: React.FC<{from: number; to?: number; children: React.ReactNode}> = ({from, to, children}) => {
  const frame = useCurrentFrame();
  const leave = to === undefined ? 1 : interpolate(frame, [to - 12, to], [1, 0], CLAMP);
  return (
    <div
      style={{
        position: 'absolute',
        left: 120,
        top: 150,
        fontSize: 60,
        fontWeight: 450,
        letterSpacing: -1.5,
        opacity: fade(frame, from + 6) * leave,
        translate: rise(frame, from + 6, 16),
      }}
    >
      {children}
    </div>
  );
};

// One agent's laptop: a screen with the part's name, and the agent as a dot on it.
const Laptop: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const start = 40 + index * 6;
  const late = index === LATE;
  const here = late ? fade(frame, JOINS_AT, 12) : 1;
  return (
    <div
      style={{
        position: 'absolute',
        top: ROW_Y,
        width: TILE,
        left: tileX(index),
        translate: rise(frame, start),
        opacity: fade(frame, start, 10),
      }}
    >
      <div
        style={{
          height: 132,
          borderRadius: 14,
          background: CARD,
          border: `2px ${late && here < 1 ? 'dashed' : 'solid'} ${C.muted}${late && here < 0.5 ? '70' : '48'}`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
        }}
      >
        <div style={{width: 26, height: 26, borderRadius: 26, background: C.blue, opacity: here, scale: String(0.6 + 0.4 * here)}} />
        <div style={{fontSize: 30, color: C.white, opacity: 0.5 + 0.5 * here}}>{PARTS[index]}</div>
      </div>
      <div style={{height: 8, margin: '6px -14px 0', borderRadius: 4, background: `${C.muted}60`}} />
    </div>
  );
};

// Beats 1 and 2: the product splits into six laptops, then the surprises land under them.
const Build: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill name="Six laptops, six surprises" style={{opacity: interpolate(frame, [WAYS_AT - 4, WAYS_AT + 10], [1, 0], CLAMP)}}>
      <div
        style={{
          position: 'absolute',
          left: 960 - 280,
          top: ROW_Y,
          width: 560,
          height: 132,
          borderRadius: 14,
          background: CARD,
          border: `2px solid ${C.blue}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 48,
          opacity: fade(frame, 10) * interpolate(frame, [34, 46], [1, 0], CLAMP),
          translate: rise(frame, 10),
        }}
      >
        PigeonPost
      </div>
      {PARTS.map((part, i) => (
        <Laptop key={part} index={i} />
      ))}
      <div
        style={{
          position: 'absolute',
          left: ROW_X,
          top: ROW_Y + 190,
          fontSize: 30,
          color: C.muted,
          opacity: fade(frame, 84) * interpolate(frame, [SURPRISES_AT - 6, SURPRISES_AT + 6], [1, 0], CLAMP),
        }}
      >
        Each agent hears only from its own developer.
      </div>

      <div style={{position: 'absolute', left: ROW_X, top: LINE_Y - 2, width: ROW_W, height: 4, borderRadius: 2, background: `${C.muted}30`, opacity: fade(frame, SURPRISES_AT, 10)}} />
      <div
        style={{
          position: 'absolute',
          left: ROW_X,
          top: LINE_Y - 2,
          height: 4,
          borderRadius: 2,
          background: C.muted,
          width: interpolate(frame, [LINE_FROM, LINE_TO], [0, ROW_W], CLAMP),
        }}
      />
      {SURPRISES.map((label, k) => {
        const at = surpriseAt(k);
        const above = k % 2 === 0;
        return (
          <React.Fragment key={label}>
            <div
              style={{
                position: 'absolute',
                left: surpriseX(k) - 12,
                top: LINE_Y - 12,
                width: 24,
                height: 24,
                borderRadius: 4,
                rotate: '45deg',
                background: C.amber,
                opacity: fade(frame, at, 6),
                translate: `0px ${interpolate(frame, [at, at + 12], [-28, 0], {...CLAMP, easing: ENTER})}px`,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: surpriseX(k) - 200,
                width: 400,
                top: above ? LINE_Y - 78 : LINE_Y + 34,
                textAlign: 'center',
                fontSize: 30,
                color: C.white,
                opacity: fade(frame, at + 4, 10),
              }}
            >
              {label}
            </div>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// Beat 3. The same six agents three times: on their own, around a chat file, around Midflight.
const WAYS = [
  {title: 'No channel', sub: "Agents can't talk to each other", hub: null},
  {title: 'Team chat', sub: 'One shared file, read and written by all', hub: 'chat'},
  {title: 'Midflight', sub: 'Claim first, check in, changes to who they affect', hub: 'midflight'},
] as const;
const RING = 108;

const Way: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const {title, sub, hub} = WAYS[index];
  const start = WAYS_AT + 14 + index * 24;
  const stroke = hub === 'midflight' ? C.blue : C.muted;
  return (
    <div
      style={{
        position: 'absolute',
        left: 120 + index * 570,
        top: 340,
        width: 540,
        height: 500,
        borderRadius: 18,
        background: CARD,
        border: `1px solid ${C.muted}38`,
        opacity: fade(frame, start),
        translate: rise(frame, start),
      }}
    >
      <svg width={540} height={320} style={{position: 'absolute', top: 10}}>
        {PARTS.map((part, i) => {
          const angle = (i / PARTS.length) * Math.PI * 2 - Math.PI / 2;
          const x = 270 + Math.cos(angle) * RING;
          const y = 160 + Math.sin(angle) * RING;
          const drawn = interpolate(frame, [start + 20 + i * 3, start + 38 + i * 3], [1, 0], {...CLAMP, easing: TRAVEL});
          return (
            <React.Fragment key={part}>
              {hub ? <line x1={x} y1={y} x2={270} y2={160} stroke={stroke} strokeWidth={2.5} strokeDasharray={RING} strokeDashoffset={RING * drawn} opacity={0.75} /> : null}
              <circle cx={x} cy={y} r={13} fill={C.blue} />
            </React.Fragment>
          );
        })}
        {hub === 'chat' ? (
          <g opacity={fade(frame, start + 14, 10)}>
            <rect x={242} y={124} width={56} height={72} rx={7} fill={CARD} stroke={C.white} strokeWidth={2.5} />
            {[142, 156, 170].map((y) => (
              <line key={y} x1={254} x2={286} y1={y} y2={y} stroke={C.white} strokeWidth={2.5} />
            ))}
          </g>
        ) : null}
        {hub === 'midflight' ? (
          <g opacity={fade(frame, start + 14, 10)}>
            <circle cx={270} cy={160} r={34} fill={CARD} stroke={C.blue} strokeWidth={3} />
            <circle cx={270} cy={160} r={12} fill={C.blue} />
          </g>
        ) : null}
      </svg>
      <div style={{position: 'absolute', top: 340, width: '100%', textAlign: 'center', fontSize: 44, fontWeight: 450, letterSpacing: -1}}>{title}</div>
      <div style={{position: 'absolute', top: 406, left: 40, right: 40, textAlign: 'center', fontSize: 28, lineHeight: 1.3, color: C.muted}}>{sub}</div>
    </div>
  );
};

// Beat 4. The six branches slide together into one product, then twenty checks run on it.
const CHECKS = 20;
const BOX = 54;
const BOX_GAP = 16;
const BOXES_X = (1920 - (CHECKS * BOX + (CHECKS - 1) * BOX_GAP)) / 2;
const MERGE_AT = SCORE_AT + 30;
const CHECKS_AT = SCORE_AT + 74;
const EVERY = 4;

const Score: React.FC = () => {
  const frame = useCurrentFrame();
  const run = Math.max(0, Math.min(CHECKS, Math.floor((frame - CHECKS_AT) / EVERY) + 1));
  return (
    <AbsoluteFill name="Merge and twenty checks" style={{opacity: fade(frame, SCORE_AT + 8) * interpolate(frame, [TABLE_AT - 4, TABLE_AT + 10], [1, 0], CLAMP)}}>
      {PARTS.map((part, i) => {
        // Once the six touch, only the outer corners of the bar stay round.
        const inner = interpolate(frame, [MERGE_AT + 18, MERGE_AT + 30], [10, 0], CLAMP);
        const left = i === 0 ? 10 : inner;
        const right = i === PARTS.length - 1 ? 10 : inner;
        return (
          <div
            key={part}
            style={{
              position: 'absolute',
              top: 410,
              height: 76,
              width: 150,
              background: i % 2 ? `${C.blue}c0` : C.blue,
              borderRadius: `${left}px ${right}px ${right}px ${left}px`,
              left: interpolate(frame, [MERGE_AT, MERGE_AT + 30], [tileX(i) + 45, 510 + i * 150], {...CLAMP, easing: TRAVEL}),
            }}
          />
        );
      })}
      <div style={{position: 'absolute', top: 502, width: 1920, textAlign: 'center', fontSize: 30, color: C.muted, opacity: fade(frame, MERGE_AT + 30, 10)}}>
        Six branches, merged into one product
      </div>
      {Array.from({length: CHECKS}, (_, k) => {
        const filled = fade(frame, CHECKS_AT + k * EVERY, 5);
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              top: 630,
              left: BOXES_X + k * (BOX + BOX_GAP),
              width: BOX,
              height: BOX,
              boxSizing: 'border-box',
              borderRadius: 8,
              border: `2px solid ${C.muted}90`,
              background: `rgba(242, 237, 225, ${0.88 * filled})`,
              opacity: fade(frame, MERGE_AT + 34 + k, 8),
            }}
          />
        );
      })}
      <div style={{position: 'absolute', top: 716, width: 1920, textAlign: 'center', fontSize: 34, opacity: fade(frame, CHECKS_AT - 6, 10), fontVariantNumeric: 'tabular-nums'}}>
        {run} of {CHECKS} automated checks run
      </div>
      <div
        style={{
          position: 'absolute',
          top: 810,
          width: 1920,
          textAlign: 'center',
          fontSize: 30,
          color: C.muted,
          opacity: fade(frame, CHECKS_AT + CHECKS * EVERY + 8),
          translate: rise(frame, CHECKS_AT + CHECKS * EVERY + 8, 16),
        }}
      >
        A failed check goes to a fixer agent, and its cost counts against that approach.
      </div>
    </AbsoluteFill>
  );
};

// The results. No channel and team chat are runs N1 and A1 (October 10); Midflight's
// checks and fix rounds are run B2 (October 11). Midflight's cost and tokens are from a
// later run on another laptop, given by Somesh on October 11; that run is not recorded in
// the midflight repo, where B2 has $2.35 and 5.17M. Cost and tokens count the building
// agents plus the fixer. Edit the words and numbers here; `strong` makes a cell stand out.
const COLUMNS = ['No channel', 'Team chat', 'Midflight'];
const ROWS: {label: string; values: string[]; strong?: number}[] = [
  {label: 'Checks passing at merge', values: ['13 of 20', '18 of 20', '20 of 20'], strong: 2},
  {label: 'Fix rounds needed', values: ['2', '1', '0'], strong: 2},
  {label: 'Cost, including rework', values: ['$2.06', '$1.88', '$1.75']},
  {label: 'Tokens, including rework', values: ['3.73M', '4.13M', '3.90M']},
];
const FOOTNOTE = 'One trial per approach, on a case designed around mid-build changes.';
const TABLE_X = 120;
const LABEL_W = 600;
const COLUMN_W = 360;
const TABLE_Y = 330;
const ROW_H = 104;

const Results: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill name="Results" style={{opacity: fade(frame, TABLE_AT + 10, 18)}}>
      <div
        style={{
          position: 'absolute',
          left: TABLE_X + LABEL_W + 2 * COLUMN_W,
          top: TABLE_Y - 16,
          width: COLUMN_W,
          height: (ROWS.length + 1) * ROW_H + 32,
          borderRadius: 18,
          background: `${C.blue}14`,
          border: `1px solid ${C.blue}60`,
        }}
      />
      {COLUMNS.map((column, c) => (
        <div
          key={column}
          style={{
            position: 'absolute',
            left: TABLE_X + LABEL_W + c * COLUMN_W,
            top: TABLE_Y,
            width: COLUMN_W,
            height: ROW_H,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 36,
            color: c === 2 ? C.blue : C.muted,
          }}
        >
          {column}
        </div>
      ))}
      {ROWS.map((row, r) => {
        const top = TABLE_Y + (r + 1) * ROW_H;
        return (
          <React.Fragment key={row.label}>
            <div style={{position: 'absolute', left: TABLE_X, top, width: LABEL_W + 3 * COLUMN_W, height: 1, background: `${C.muted}38`}} />
            <div style={{position: 'absolute', left: TABLE_X, top, width: LABEL_W, height: ROW_H, display: 'flex', alignItems: 'center', fontSize: 36}}>{row.label}</div>
            {row.values.map((value, c) => (
              <div
                key={c}
                style={{
                  position: 'absolute',
                  left: TABLE_X + LABEL_W + c * COLUMN_W,
                  top,
                  width: COLUMN_W,
                  height: ROW_H,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 46,
                  fontWeight: row.strong === c ? 650 : 400,
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {value}
              </div>
            ))}
          </React.Fragment>
        );
      })}
      <div style={{position: 'absolute', left: TABLE_X, top: TABLE_Y + (ROWS.length + 1) * ROW_H + 60, fontSize: 28, color: C.muted}}>{FOOTNOTE}</div>
    </AbsoluteFill>
  );
};

export const BenchmarkSetup: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{fontFamily: 'Inter Variable, sans-serif', color: C.white}}>
      <AbsoluteFill name="Backdrop" style={{background: C.bg, opacity: fade(frame, 0, 18)}} />
      <div style={{position: 'absolute', left: 120, top: 92, fontSize: 34, color: C.blue, opacity: fade(frame, 8) * interpolate(frame, [TABLE_AT - 12, TABLE_AT], [1, 0], CLAMP)}}>
        How the benchmark works
      </div>
      <div style={{position: 'absolute', left: 120, top: 92, fontSize: 34, color: C.blue, opacity: fade(frame, TABLE_AT + 6)}}>What it found</div>
      <Caption from={8} to={SURPRISES_AT}>
        Six agents, six laptops, one plan.
      </Caption>
      <Caption from={SURPRISES_AT} to={WAYS_AT}>
        Six surprises after the plan is written.
      </Caption>
      <Caption from={WAYS_AT} to={SCORE_AT}>
        Three ways to coordinate. Same model, same instructions.
      </Caption>
      <Caption from={SCORE_AT} to={TABLE_AT}>
        Merged, then 20 automated checks.
      </Caption>
      <Caption from={TABLE_AT}>PigeonPost: 6 agents, 20 checks.</Caption>
      <Build />
      <AbsoluteFill name="Three ways" style={{opacity: interpolate(frame, [SCORE_AT - 4, SCORE_AT + 10], [1, 0], CLAMP)}}>
        {WAYS.map((way, i) => (
          <Way key={way.title} index={i} />
        ))}
      </AbsoluteFill>
      <Score />
      <Results />
    </AbsoluteFill>
  );
};
