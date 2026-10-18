import React from 'react';
import {AbsoluteFill, Freeze, Sequence, useCurrentFrame} from 'remotion';
import {Vector3} from 'three';
import {Assignment, FlightChapter} from '../merged-story/MergedStory';
import {LeadIntro} from '../lead-intro/LeadIntro';
import {baseline, C, clamp, ease, FPS, mix, project} from '../flight3d/model';

// Original delegation, one failed merge, then a native version of the HTML's
// one-second chip handoff. The original flight resumes exactly at its handoff pose.
const PROJECT_FRAMES = 216;
const LEAD_FRAMES = 270;
const HANDOFF_FRAMES = 30;
const FLIGHT_ENTRY_FRAME = 111; // HTML's source-video time 20.2s, flight time 3.7s.
const FLIGHT_FRAMES = 1005 - FLIGHT_ENTRY_FRAME;
export const HANDOFF_AT = PROJECT_FRAMES + LEAD_FRAMES;
export const REORDERED_OPENING_FRAMES = HANDOFF_AT + HANDOFF_FRAMES + FLIGHT_FRAMES;
const PACE = 49.5 / 36.5;

const Flight: React.FC = () => {
  const frame = useCurrentFrame();
  const originalSeconds = (frame + FLIGHT_ENTRY_FRAME) / FPS + 6.5;
  return <FlightChapter frameOffset={FLIGHT_ENTRY_FRAME} sameAgentPings audioVolume={1 - ease((originalSeconds - 38.5) / 1.5)}/>;
};

export const LeadPlaneHandoff: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = clamp(frame / HANDOFF_FRAMES);
  const eased = ease(progress);
  const native = clamp((progress - 0.85) / 0.15);
  const flightTime = FLIGHT_ENTRY_FRAME / FPS * PACE;
  return <AbsoluteFill style={{background: C.bg, fontFamily: 'Inter Variable, sans-serif'}}>
    {/* Keep the destination pose stable while the chips travel, as in the HTML. */}
    <Freeze frame={FLIGHT_ENTRY_FRAME}>
      <FlightChapter sameAgentPings agentLabelsOpacity={native} audioVolume={0}/>
    </Freeze>
    {/* Fade only the outgoing scene. The moving labels are rendered separately. */}
    <AbsoluteFill style={{opacity: 1 - eased}}>
      <Freeze frame={LEAD_FRAMES - 1}><LeadIntro singleAttempt hideAgents fadeOut={false}/></Freeze>
    </AbsoluteFill>
    {[0, 1].map(index => {
      const from = {x: index ? 1663 : 257, y: 619};
      const to = project(baseline(flightTime, index).pos.clone().add(new Vector3(0, 1, 0)), flightTime);
      const x = mix(from.x, to.left, eased);
      const y = mix(from.y, to.top, eased) - 55 * Math.sin(Math.PI * progress);
      const width = 174 * (1 - 0.2 * eased);
      const height = 54 * (1 - 0.2 * eased);
      const color = index ? C.white : C.blue;
      return <React.Fragment key={index}>
        <div style={{position: 'absolute', left: x - width / 2, top: y - height / 2, width, height, borderRadius: 9, background: '#101923', border: `1px solid ${color}80`, opacity: (1 - eased) * (1 - native)}}>
          <span style={{position: 'absolute', left: 21, top: height / 2 - 5.5, width: 11, height: 11, borderRadius: index ? 11 : 1, background: color}}/>
        </div>
        <div style={{position: 'absolute', left: x + 14 * (1 - eased), top: y, transform: 'translate(-50%, -50%)', fontSize: 28 - 9 * eased, letterSpacing: 2 * eased, color, whiteSpace: 'nowrap', opacity: 1 - native}}>
          Agent {index ? 'B' : 'A'}
        </div>
      </React.Fragment>;
    })}
  </AbsoluteFill>;
};

export const ReorderedOpening: React.FC = () => <AbsoluteFill style={{background: C.bg}}>
  <Sequence name="One project — original delegation animation" durationInFrames={PROJECT_FRAMES}>
    <Assignment/>
  </Sequence>
  <Sequence name="Team lead — one failed merge" from={PROJECT_FRAMES} durationInFrames={LEAD_FRAMES}>
    <LeadIntro singleAttempt fadeOut={false}/>
  </Sequence>
  <Sequence name="Agent chips move directly onto the planes" from={HANDOFF_AT} durationInFrames={HANDOFF_FRAMES}>
    <LeadPlaneHandoff/>
  </Sequence>
  <Sequence name="Continuous flight and team animation" from={HANDOFF_AT + HANDOFF_FRAMES} durationInFrames={FLIGHT_FRAMES}>
    <Flight/>
  </Sequence>
</AbsoluteFill>;
