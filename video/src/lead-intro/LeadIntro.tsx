import React from 'react';
import {AbsoluteFill, Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';
import {C} from '../flight3d/model';

// Original team-lead/bridge animation. The pitch uses singleAttempt to keep the
// first failed merge, omit the retry, and hand its agent chips onto the planes.
// Other standalone/legacy compositions retain the original two-attempt version.
// All keyframes use this scene's local clock.

export const LEAD_INTRO_FRAMES = 300;

const PASS = '#9ee0b1';
const CARD = '#101923';

// Each half of the bridge is this long and this tall; the halves meet at x = 960.
const SPAN = 742;
const DECK = 32;
const TRUSS = Array.from({length: 17}, (_, i) => `${i === 0 ? 'M' : 'L'}${(i * SPAN) / 16} ${i % 2 ? 4 : 4 + DECK}`).join(' ');

const Headline: React.FC<{name: string; from: number; to: number; children: React.ReactNode}> = ({name, from, to, children}) => {
  const frame = useCurrentFrame();
  return (
    <Interactive.Div
      name={name}
      style={{
        position: 'absolute',
        left: 90,
        right: 90,
        top: 100,
        fontSize: 64,
        fontWeight: 450,
        letterSpacing: -2,
        opacity: interpolate(frame, [from, from + 14, to, to + 8], [0, 1, 1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }),
      }}
    >
      {children}
    </Interactive.Div>
  );
};

// The lead: ProblemOpening's developer, larger, with a merge on the screen instead of code.
const Lead: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <svg viewBox="0 0 220 210" width={286} height={273} style={{position: 'absolute', left: 817, top: 215}} fill="none" strokeWidth={1.5} strokeLinecap="round">
        <circle
          cx={110}
          cy={35}
          r={20}
          stroke={C.white}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={interpolate(frame, [8, 26], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
        />
        <path
          d="M68 105V88C68 50 152 50 152 88V105"
          stroke={C.white}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={interpolate(frame, [12, 32], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
        />
        <rect
          x={25}
          y={100}
          width={170}
          height={95}
          rx={9}
          fill={C.bg}
          stroke={C.muted}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={interpolate(frame, [16, 42], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
        />
        <path
          d="M10 199H210"
          stroke={C.muted}
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={interpolate(frame, [30, 44], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
        />
        {/* Two branches joining into one. It turns amber when the merge fails. */}
        {[C.blue, C.amber].map((color) => (
          <g
            key={color}
            stroke={color}
            opacity={
              color === C.blue
                ? interpolate(frame, [36, 48, 172, 180], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
                : interpolate(frame, [172, 180], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
            }
          >
            <path d="M88 133C104 133 104 147 120 147M88 161C104 161 104 147 120 147M120 147H130" />
            <circle cx={84} cy={133} r={4} />
            <circle cx={84} cy={161} r={4} />
            <circle cx={134} cy={147} r={4} />
          </g>
        ))}
      </svg>
      <Interactive.Div
        name="Label: Team lead"
        style={{
          position: 'absolute',
          left: 0,
          top: 490,
          width: 1920,
          textAlign: 'center',
          fontSize: 32,
          opacity: interpolate(frame, [30, 44], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Team lead
      </Interactive.Div>
      {/* Stays for three seconds, into the start of the build, so it can be read. */}
      <Interactive.Div
        name="What the lead does"
        style={{
          position: 'absolute',
          left: 0,
          top: 544,
          width: 1920,
          textAlign: 'center',
          fontSize: 30,
          color: C.muted,
          opacity: interpolate(frame, [44, 58, 128, 142], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        Owns the plan. Merges everyone&apos;s work.
      </Interactive.Div>
    </>
  );
};

// One agent's label above its bank, with "works" once its half is nearly built.
const Agent: React.FC<{side: 'left' | 'right'; label: string; color: string}> = ({side, label, color}) => {
  const frame = useCurrentFrame();
  return (
    <Interactive.Div
      name={label}
      style={{
        position: 'absolute',
        [side]: 170,
        top: 592,
        display: 'flex',
        flexDirection: side === 'left' ? 'row' : 'row-reverse',
        alignItems: 'center',
        gap: 22,
        opacity: interpolate(frame, [102, 116], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          padding: '9px 20px',
          borderRadius: 9,
          background: CARD,
          border: `1px solid ${color}65`,
          fontSize: 28,
          color,
        }}
      >
        <span style={{width: 11, height: 11, background: color, borderRadius: side === 'left' ? 1 : 11}} />
        {label}
      </div>
      <div
        style={{
          fontSize: 28,
          color: PASS,
          opacity: interpolate(frame, [156, 166, 228, 236], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      >
        works ✓
      </div>
    </Interactive.Div>
  );
};

// Half a bridge, built outward from its own bank. Its width is how much is built: it
// grows to the middle and recoils. singleAttempt keeps the failed bridge there;
// the legacy version pulls back and tries again.
const Span: React.FC<{side: 'left' | 'right'; top: number; color: string; singleAttempt?: boolean}> = ({side, top, color, singleAttempt = false}) => {
  const frame = useCurrentFrame();
  return (
    <Interactive.Div
      name={side === 'left' ? "Agent A's half" : "Agent B's half"}
      style={{
        position: 'absolute',
        [side]: 210,
        top,
        height: DECK + 8,
        opacity: interpolate(frame, [108, 116], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        width: singleAttempt ? interpolate(frame, [114, 172], [0, SPAN], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.35, 0, 0.85, 0.85)}) : interpolate(frame, [114, 172, 234, 254, 258, 300], [0, SPAN, SPAN, 330, 330, 640], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: [
            Easing.bezier(0.35, 0, 0.85, 0.85),
            Easing.linear,
            Easing.bezier(0.65, 0, 0.35, 1),
            Easing.linear,
            Easing.bezier(0.35, 0, 0.85, 0.85),
          ],
        }),
        translate: interpolate(frame, [172, 175, 182], side === 'left' ? ['0px 0px', '-7px 0px', '0px 0px'] : ['0px 0px', '7px 0px', '0px 0px'], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        }),
      }}
    >
      <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden'}}>
        <svg
          viewBox={`0 0 ${SPAN} ${DECK + 8}`}
          width={SPAN}
          height={DECK + 8}
          style={{position: 'absolute', top: 0, [side]: 0, scale: side === 'left' ? '1 1' : '-1 1'}}
          fill="none"
          stroke={color}
          strokeWidth={2}
        >
          <path d={`M0 4H${SPAN}M0 ${4 + DECK}H${SPAN}`} />
          <path d={TRUSS} strokeWidth={1.5} opacity={0.55} strokeLinejoin="round" />
        </svg>
      </div>
      {/* The end being built: the agent's colour, then amber while the halves are stuck. */}
      <div style={{position: 'absolute', [side === 'left' ? 'right' : 'left']: -3, top: 0, width: 6, height: DECK + 8, borderRadius: 3, background: color}} />
      <div
        style={{
          position: 'absolute',
          [side === 'left' ? 'right' : 'left']: -3,
          top: 0,
          width: 6,
          height: DECK + 8,
          borderRadius: 3,
          background: C.amber,
          opacity: singleAttempt ? interpolate(frame, [172, 176], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : interpolate(frame, [172, 176, 230, 240], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      />
    </Interactive.Div>
  );
};

// What happens in the middle: the merge, the ring around the gap, and the attempt count.
const Merge: React.FC<{singleAttempt?: boolean}> = ({singleAttempt = false}) => {
  const frame = useCurrentFrame();
  return (
    <>
      <Interactive.Div
        name="Glow on the gap"
        style={{
          position: 'absolute',
          left: 660,
          top: 541,
          width: 600,
          height: 400,
          background: `radial-gradient(closest-side, ${C.amber}40, transparent)`,
          opacity: singleAttempt ? interpolate(frame, [172, 180, 210], [0, 1, 0.7], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : interpolate(frame, [172, 180, 228, 240], [0, 1, 0.7, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      />
      <Interactive.Div
        name="Merge attempt"
        style={{
          position: 'absolute',
          left: 0,
          top: 546,
          width: 1920,
          display: 'flex',
          justifyContent: 'center',
          opacity: interpolate(frame, [176, 188], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          translate: interpolate(frame, [176, 190], ['0px 12px', '0px 0px'], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            padding: '9px 20px',
            borderRadius: 9,
            background: CARD,
            border: `1px solid ${C.amber}`,
            fontSize: 28,
            color: C.amber,
          }}
        >
          <span style={{width: 11, height: 11, background: C.amber, borderRadius: 11}} />
          Merge attempt
          {singleAttempt ? <span>1</span> : <>
          <div style={{position: 'relative', width: 17, height: 36}}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                lineHeight: '36px',
                opacity: interpolate(frame, [244, 250], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                translate: interpolate(frame, [244, 250], ['0px 0px', '0px -14px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
              }}
            >
              1
            </div>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                lineHeight: '36px',
                opacity: interpolate(frame, [248, 254], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
                translate: interpolate(frame, [248, 256], ['0px 14px', '0px 0px'], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
              }}
            >
              2
            </div>
          </div>
          </>}
        </div>
      </Interactive.Div>
      <Interactive.Div
        name="Line to the gap"
        style={{
          position: 'absolute',
          left: 959,
          top: 608,
          width: 0,
          borderLeft: `2px dashed ${C.amber}`,
          height: interpolate(frame, [182, 194], [0, 63], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.bezier(0.65, 0, 0.35, 1),
          }),
          opacity: singleAttempt ? 1 : interpolate(frame, [228, 238], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        }}
      />
      <Interactive.Div
        name="Ring around the gap"
        style={{
          position: 'absolute',
          left: 890,
          top: 671,
          width: 140,
          height: 140,
          boxSizing: 'border-box',
          borderRadius: 70,
          border: `2px solid ${C.amber}`,
          opacity: singleAttempt ? interpolate(frame, [173, 180], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : interpolate(frame, [173, 180, 228, 238], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          scale: interpolate(frame, [173, 188], [0.55, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: 'perceptual-scale',
          }),
        }}
      />
      <Interactive.Div
        name="Pulse"
        style={{
          position: 'absolute',
          left: 890,
          top: 671,
          width: 140,
          height: 140,
          boxSizing: 'border-box',
          borderRadius: 70,
          border: `2px solid ${C.amber}`,
          opacity: interpolate(frame, [174, 178, 210], [0, 0.7, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          scale: interpolate(frame, [174, 210], [1, 2.6], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: 'perceptual-scale',
          }),
        }}
      />
    </>
  );
};

export const LeadIntro: React.FC<{singleAttempt?: boolean; hideAgents?: boolean; fadeOut?: boolean}> = ({singleAttempt = false, hideAgents = false, fadeOut = true}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: 'Inter Variable, sans-serif', color: C.white}}>
      <AbsoluteFill
        name="Scene"
        style={{opacity: fadeOut ? interpolate(frame, [284, 298], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1}}
      >
        <Headline name="Headline: the person" from={6} to={96}>
          Meet the team lead.
        </Headline>
        <Headline name="Headline: building alone" from={106} to={164}>
          Every agent builds its part alone.
        </Headline>
        <Headline name="Headline: the merge" from={174} to={singleAttempt ? LEAD_INTRO_FRAMES : 226}>
          At merge, the parts don&apos;t fit.
        </Headline>
        {!singleAttempt && <Headline name="Headline: the cost" from={236} to={LEAD_INTRO_FRAMES}>
          Finished work gets rebuilt. Again.
        </Headline>}

        <Lead />

        <svg
          viewBox="0 0 1920 1080"
          width={1920}
          height={1080}
          style={{position: 'absolute', opacity: interpolate(frame, [100, 116], [0, 0.6], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}
          fill="none"
          stroke={C.muted}
          strokeWidth={2}
          strokeLinecap="round"
        >
          <path d="M250 724V900M290 724V900M170 900H370" />
          <path d="M1630 794V900M1670 794V900M1550 900H1750" />
        </svg>
        {!hideAgents && <>
          <Agent side="left" label="Agent A" color={C.blue} />
          <Agent side="right" label="Agent B" color={C.white} />
        </>}

        <Merge singleAttempt={singleAttempt} />
        <Span side="left" top={686} color={C.blue} singleAttempt={singleAttempt} />
        <Span side="right" top={756} color={C.white} singleAttempt={singleAttempt} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
