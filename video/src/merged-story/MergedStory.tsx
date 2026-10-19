import React from 'react';
import {AbsoluteFill,Sequence,useCurrentFrame} from 'remotion';
import {FlightSequence} from '../flight3d/FlightFilm';
import {ProblemOpening} from '../flight3d/ProblemOpening';
import {C,FPS,ease} from '../flight3d/model';

export const MERGED_SECONDS=43;
const FLIGHT_START=6.5,PACE=49.5/(MERGED_SECONDS-FLIGHT_START);
export function Assignment({timeOffset=0}:{timeOffset?:number}){
 const real=useCurrentFrame()/FPS+timeOffset,t=Math.max(0,(real-1)*2);
 return <ProblemOpening time={t} exitAt={13} flightStart={(FLIGHT_START-1)*2} headlineOpacity={ease((real-.2)/.7)} diagramOpacity={ease((real-1.6)/.55)} taskDelay={1.5}
  headlineOverride="One project. Different tasks. Multiple developers."/>;
}
export function FlightChapter({audioVolume=1,sameAgentPings=false,frameOffset=0,agentLabelsOpacity=1}:{audioVolume?:number;sameAgentPings?:boolean;frameOffset?:number;agentLabelsOpacity?:number}){
 const raw=(useCurrentFrame()+frameOffset)/FPS*PACE;
 // Skip the fourth flight under the fade, directly after the third commit.
 const skip=raw>=19?4:0,t=raw+skip;
 const reveal=t>=23&&t<27;
 const textFade=t<23?1-ease((t-18.05)/.8):t<27?ease((t-23.1)/.95)*(1-ease((t-26.1)/.9)):ease((t-27)/.75);
 const veil=t<23?ease((t-18.25)/.75):1-ease((t-23)/1.15);
 const lift=reveal?(1-ease((t-23.1)/.95))*14:0;
 const title=sameAgentPings&&t>=27&&t<29.4?'':t>=38.7?'Now imagine an entire team of agents.':reveal?'Meet Midflight':t>=27?'Share context. Adjust. Keep moving.':t>=8?'Commit. Discover. Repeat.':'Agents working in parallel';
 return <FlightSequence timeOffset={skip+frameOffset/FPS*PACE} timeScale={PACE} agentLabelsOpacity={agentLabelsOpacity} expandTeam audioVolume={audioVolume} sameAgentPings={sameAgentPings}
  goalLabel="Project goal" headlineOverride={title} headlineCentered={reveal} headlineOpacity={textFade} headlineLift={lift} sceneVeil={veil}/>;
}
export const MergedStory:React.FC<{audioVolume?:number;sameAgentPings?:boolean}>=({audioVolume=1,sameAgentPings=false})=> <AbsoluteFill style={{background:C.bg}}>
 <Sequence from={FLIGHT_START*FPS}><FlightChapter audioVolume={audioVolume} sameAgentPings={sameAgentPings}/></Sequence>
 <Sequence durationInFrames={Math.round(9.25*FPS)}><Assignment/></Sequence>
</AbsoluteFill>;
