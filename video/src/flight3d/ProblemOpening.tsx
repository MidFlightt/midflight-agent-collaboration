import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C, FPS, FLIGHT_OFFSET, baseline, ease, mix, project} from './model';

export const ProblemOpening: React.FC<{compact?:number;exitAt?:number;flightStart?:number;headlineOverride?:string;time?:number;headlineOpacity?:number;diagramOpacity?:number;taskDelay?:number}> = ({compact=0,exitAt=21.5,flightStart=FLIGHT_OFFSET,headlineOverride,time,headlineOpacity=1,diagramOpacity=1,taskDelay=0}) => {
  const frameTime=useCurrentFrame()/FPS,t=time??frameTime;
  const enter=(at:number)=>ease((t-at)/1);
  const transfer=ease((t-exitAt)/3.5),fade=1-ease((t-exitAt-.5)/1.8),reveal=ease((t-exitAt-.5)/2.5);
  const headline=headlineOverride??(t<5.5?'One project. Two different tasks.':t<11?'Each developer delegates their task.':t<18?'Different tasks. One shared project.':'Their assumptions start to diverge.');
  const panel=(at:number):React.CSSProperties=>({opacity:enter(at)*fade,transform:`translateY(${(1-enter(at))*20}px)`});
  return <AbsoluteFill style={{fontFamily:'Inter Variable, sans-serif',color:C.white,overflow:'hidden'}}>
    <AbsoluteFill style={{background:C.bg,opacity:1-reveal}}/>
    <div style={{position:'absolute',left:90,right:90,top:100,fontSize:64,fontWeight:450,letterSpacing:-2,opacity:headlineOpacity*(1-ease((t-exitAt+.5)/1.3))}}>{headline}</div>
    <AbsoluteFill style={{opacity:diagramOpacity}}>
    <svg width="1920" height="1080" style={{position:'absolute',inset:0,opacity:fade}}>
      {[0,1].map(i=><React.Fragment key={i}>
        <path d={`M960 ${mix(420,340,compact)} C960 ${mix(470,355,compact)} ${mix(i?1260:660,i?1310:610,compact)} ${mix(460,355,compact)} ${mix(i?1260:660,i?1310:610,compact)} ${mix(510,375,compact)}`} fill="none" stroke={C.muted} strokeWidth="1.5" pathLength="1" strokeDasharray="1" strokeDashoffset={1-enter(3.2+i*.5)} opacity=".5"/>
        <path d={`M${mix(i?1260:660,i?1310:610,compact)} ${mix(665,550,compact)}V${mix(785,575,compact)}`} fill="none" stroke={i?C.white:C.blue} strokeWidth="1.5" pathLength="1" strokeDasharray="1" strokeDashoffset={1-enter(7+i*.7)} opacity=".5"/>

      </React.Fragment>)}
    </svg>
    <div style={{position:'absolute',left:785,top:mix(225,205,compact),width:350,height:mix(195,135,compact),border:`1px solid ${C.muted}55`,borderRadius:16,background:'#101923',padding:mix(28,22,compact),boxSizing:'border-box',...panel(.3)}}>
      <div style={{fontSize:27,letterSpacing:-.5,marginBottom:mix(25,16,compact)}}>Project brief</div>
      {[240,190,225,150].map((width,i)=><div key={i} style={{height:mix(3,2,compact),width,background:C.muted,opacity:.23,marginTop:mix(14,9,compact)}}/>)}
    </div>
    {[0,1].map(i=><div key={`developer-${i}`} style={{position:'absolute',left:mix(i?1260:660,i?1310:610,compact)-110,top:mix(510,375,compact),width:220,...panel(2+i*.6)}}>
      <svg width="220" height={mix(155,135,compact)} viewBox="0 0 220 210">
        <circle cx="110" cy="35" r="20" fill="none" stroke={C.white} strokeWidth="2"/>
        <path d="M68 105V88C68 50 152 50 152 88V105" fill="none" stroke={C.white} strokeWidth="2"/>
        <rect x="25" y="100" width="170" height="95" rx="9" fill={C.bg} stroke={C.muted} strokeWidth="2"/>
        <path d="M93 132l-12 12 12 12M127 132l12 12-12 12M116 130l-12 28" fill="none" stroke={i?C.white:C.blue} strokeWidth="2"/>
        <path d="M10 199H210" stroke={C.muted} strokeWidth="2"/>
      </svg>
      <div style={{textAlign:'center',fontSize:24,marginTop:10,background:C.bg,padding:'0 10px'}}>Developer {i?'B':'A'}</div>
    </div>)}
    {[0,1].map(i=>{
      const color=i?C.white:C.blue;
      const target=project(baseline(5,i).pos,Math.max(0,t-flightStart));
      const x=mix(mix(i?1260:660,i?1310:610,compact),target.left,transfer),y=mix(mix(860,635,compact),target.top,transfer);
      return <div key={i} style={{position:'absolute',left:x,top:y,width:mix(310,340,compact),height:mix(150,120,compact),transform:`translate(-50%,-50%) scale(${mix(.94+enter(7+i*.7)*.06,.04,transfer)})`,opacity:enter(7+i*.7)*(1-ease((t-exitAt-1.5)/1.2)),background:C.bg,border:`1px solid ${color}70`,borderRadius:16,display:'flex',alignItems:'center',justifyContent:'center',gap:16,boxSizing:'border-box'}}>
        <span style={{width:12,height:12,background:color,borderRadius:i?12:2,transform:'translateY(-17px)'}}/><span style={{fontSize:33,color,transform:'translateY(-17px)'}}>Agent {i?'B':'A'}</span>
      </div>;
    })}
    {[0,1].map(i=>{
      const color=i?C.white:C.blue,branch=i?1260:660;
      const split=ease((t-taskDelay-3.4-i*.5)/1.8),delegate=ease((t-taskDelay-8.3-i*.6)/1.8);
      const x=mix(960,branch,split),y=mix(mix(365,455,split),894,delegate);
      const target=project(baseline(5,i).pos,Math.max(0,t-flightStart));
      return <div key={`task-${i}`} style={{position:'absolute',left:mix(mix(x,i?1310:610,compact),target.left,transfer),top:mix(mix(y,668,compact),target.top,transfer),width:mix(150,135,compact),height:mix(42,30,compact),transform:`translate(-50%,-50%) scale(${mix(1,.04,transfer)})`,opacity:enter(3.1+i*.5+taskDelay)*(1-ease((t-exitAt-1.5)/1.2)),background:'#101923',border:`1px solid ${color}65`,borderRadius:7,display:'flex',alignItems:'center',justifyContent:'center',gap:12,color,fontSize:mix(22,19,compact)}}>
        <span style={{width:9,height:9,background:color,borderRadius:i?9:1}}/>Task {i?'B':'A'}
      </div>;
    })}
    </AbsoluteFill>
  </AbsoluteFill>;
};
