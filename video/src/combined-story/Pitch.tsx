import React from 'react';
import {AbsoluteFill, Freeze, Img, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {BenchmarkSetup} from './BenchmarkSetup';
import {C} from '../flight3d/model';
import {ReorderedOpening} from './ReorderedOpening';

const FPS = 30;
const asset = (name: string) => staticFile(name);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// The trimmed recording is included by default. Override its path with --props.
export const DEMO_FILE = 'demo/live-agent-demo.mp4';
export const DEMO_SECONDS = 52;
export type PitchProps = {demoFile?: string};
export const PITCH_CHAPTERS = [
  {name: 'Opening — project, team lead, planes, team of agents', seconds: 47},
  {name: 'Demo — live coding team', seconds: DEMO_SECONDS},
  {name: 'How Midflight works', seconds: 20},
  {name: 'How Midflight shares changes', seconds: 25},
  {name: 'System architecture', seconds: 20},
  {name: 'Benchmark setup', seconds: 25},
  {name: 'Benchmark results', seconds: 15},
  {name: 'Context research', seconds: 13},
  {name: 'Thank you', seconds: 5},
] as const;
export const PITCH_FRAMES = PITCH_CHAPTERS.reduce((total, chapter) => total + chapter.seconds * FPS, 0);

const Still: React.FC<{file: string}> = ({file}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: C.bg}}>
    <Img src={asset(file)} style={{width: '100%', height: '100%', objectFit: 'contain', opacity: interpolate(frame, [0, 12], [0, 1], clamp)}}/>
  </AbsoluteFill>;
};

const Title: React.FC<{title: string; subtitle?: string}> = ({title, subtitle}) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: C.bg, color: C.white, fontFamily: 'Inter Variable, sans-serif', justifyContent: 'center', alignItems: 'center'}}>
    <div style={{textAlign: 'center', opacity: interpolate(frame, [0, 18], [0, 1], clamp)}}>
      <div style={{fontSize: 112, fontWeight: 450, letterSpacing: -4}}>{title}</div>
      {subtitle && <div style={{fontSize: 32, marginTop: 28, color: C.muted}}>{subtitle}</div>}
    </div>
  </AbsoluteFill>;
};

// The existing benchmark is 20 seconds of setup plus 8 seconds of results.
// Let the setup breathe across 25 seconds; show the results animation at its
// existing speed and hold the completed table for the rest of its 15-second slot.
const BenchmarkChapter: React.FC<{results?: boolean}> = ({results = false}) => {
  const frame = useCurrentFrame();
  const originalFrame = results ? 600 + Math.min(frame, 239) : Math.min(599, Math.floor(frame * 600 / 750));
  return <Freeze frame={originalFrame}><BenchmarkSetup/></Freeze>;
};

export const Pitch: React.FC<PitchProps> = ({demoFile = DEMO_FILE}) => {
  const scenes = [
    <ReorderedOpening key="opening"/>,
    demoFile ? <OffthreadVideo key="demo" src={staticFile(demoFile)} style={{width: '100%', height: '100%', objectFit: 'contain'}}/> : <Title key="demo" title="Demo" subtitle="Demo footage to be inserted"/>,
    <Still key="works" file="flowcharts/how-midflight-works.png"/>,
    <Still key="changes" file="flowcharts/how-midflight-shares-changes.png"/>,
    <Still key="architecture" file="flowcharts/midflight-system-architecture.png"/>,
    <BenchmarkChapter key="setup"/>,
    <BenchmarkChapter key="results" results/>,
    <Still key="research" file="research/context-research.jpg"/>,
    <Title key="thanks" title="Thank you"/>,
  ];
  let start = 0;
  return <AbsoluteFill style={{background: C.bg}}>
    {PITCH_CHAPTERS.map((chapter, index) => {
      const from = start;
      const durationInFrames = chapter.seconds * FPS;
      start += durationInFrames;
      return <Sequence key={chapter.name} name={chapter.name} from={from} durationInFrames={durationInFrames}>{scenes[index]}</Sequence>;
    })}
  </AbsoluteFill>;
};
