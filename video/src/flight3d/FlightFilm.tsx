import React,{useLayoutEffect,useMemo} from 'react';
import {AbsoluteFill,Audio,Sequence,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {BufferGeometry,Float32BufferAttribute,DoubleSide,Vector3,CatmullRomCurve3} from 'three';
import {C,FPS,GOAL_X,FLIGHT_OFFSET,OPENING_SECONDS,baseline,airborne,sat,cameraAt,project,copy,windows,clamp,ease,mix,starts,ends} from './model';
import {Clouds} from './Clouds';
import {ProblemOpening} from './ProblemOpening';

const CameraMode=React.createContext(true);
function Camera({t}:{t:number}){const {camera}=useThree(),expand=React.useContext(CameraMode);useLayoutEffect(()=>{const c=sceneCamera(t,expand);camera.position.copy(c.position);camera.quaternion.copy(c.quaternion);camera.updateMatrixWorld();},[camera,t,expand]);return null;}

export function Plane({color}:{color:string}){
 const wing=useMemo(()=>{const g=new BufferGeometry();g.setAttribute('position',new Float32BufferAttribute([.28,0,0,-.45,0,1,-.18,.05,0,.28,0,0,-.18,.05,0,-.45,0,-1],3));g.computeVertexNormals();return g;},[]);
 return <group scale={.70}>
  <mesh rotation={[0,0,Math.PI/2]} castShadow><capsuleGeometry args={[.105,1.1,5,12]}/><meshStandardMaterial color={color} metalness={.42} roughness={.28}/></mesh>
  <mesh geometry={wing} castShadow><meshStandardMaterial color={color} side={DoubleSide} metalness={.4} roughness={.3}/></mesh>
  <mesh position={[-.46,.03,0]} scale={[.3,1,.48]} geometry={wing} castShadow><meshStandardMaterial color={color} side={DoubleSide} metalness={.4} roughness={.3}/></mesh>
  <mesh position={[-.54,.16,0]} rotation={[0,0,-.2]}><boxGeometry args={[.28,.30,.028]}/><meshStandardMaterial color={color}/></mesh>
  <mesh position={[.27,.09,0]} scale={[1.5,.5,1]}><sphereGeometry args={[.105,12,8]}/><meshStandardMaterial color="#152839" metalness={.6} roughness={.15}/></mesh>
  <mesh position={[-.68,0,0]}><sphereGeometry args={[.055,8,6]}/><meshBasicMaterial color={color}/></mesh>
 </group>;
}
export function Tube({points,color,radius=.015,opacity=1}:{points:Vector3[];color:string;radius?:number;opacity?:number}){
 const curve=useMemo(()=>new CatmullRomCurve3(points,false,'centripetal'),[points]);
 if(points.length<2||points[0].distanceTo(points[points.length-1])<.001)return null;
 return <mesh><tubeGeometry args={[curve,Math.min(180,points.length*2),radius,5,false]}/><meshBasicMaterial color={color} transparent opacity={opacity}/></mesh>;
}
export function Pad({x,z,color,active=false}:{x:number;z:number;color:string;active?:boolean}){return <group position={[x,.035,z]}>
 <mesh><cylinderGeometry args={[.48,.53,.07,40]}/><meshStandardMaterial color="#182a38" metalness={.55} roughness={.4}/></mesh>
 <mesh rotation={[-Math.PI/2,0,0]} position={[0,.046,0]}><ringGeometry args={[.38,.397,48]}/><meshBasicMaterial color={color} transparent opacity={active?1:.30} side={DoubleSide}/></mesh>
 <mesh position={[0,.05,0]}><boxGeometry args={[.5,.012,.025]}/><meshBasicMaterial color={color}/></mesh>
 </group>;}
function GoalMarker(){return <group position={[GOAL_X,0,0]}>
 <mesh rotation={[-Math.PI/2,0,0]} position={[0,.025,0]}><ringGeometry args={[1.15,1.19,64]}/><meshBasicMaterial color={C.white} transparent opacity={.65} side={DoubleSide}/></mesh>
 <mesh rotation={[-Math.PI/2,0,0]} position={[0,.027,0]}><ringGeometry args={[.75,.77,64]}/><meshBasicMaterial color={C.white} transparent opacity={.3} side={DoubleSide}/></mesh>
 <mesh position={[0,1.6,0]}><cylinderGeometry args={[.025,.025,3.2,10]}/><meshBasicMaterial color={C.white} transparent opacity={.6}/></mesh>
 <mesh position={[0,3.25,0]}><torusGeometry args={[.26,.018,8,40]}/><meshBasicMaterial color={C.white}/></mesh>
 <mesh position={[0,3.25,0]}><sphereGeometry args={[.055,10,10]}/><meshBasicMaterial color={C.white}/></mesh>
 </group>;}
function LandingMark({t,stop,i}:{t:number;stop:number;i:number}){
 const p=baseline(ends[stop]+.01,i).pos;
 if(t<ends[stop])return null;
 return <mesh position={[p.x,.015,p.z]} rotation={[-Math.PI/2,0,0]} scale={ease((t-ends[stop])/.45)}>
  <ringGeometry args={[.38,.395,48]}/><meshBasicMaterial color={i?C.white:C.blue} transparent opacity={.45} side={DoubleSide}/>
 </mesh>;
}
export function Satellite({t}:{t:number}){const p=sat(t),enter=ease((t-23)/2);return <group position={[p.x,p.y+(1-enter)*5,p.z]} rotation={[.18,(t-23)*.08,-.16]} scale={.82*enter}>
 <mesh castShadow><boxGeometry args={[.62,.5,.5]}/><meshStandardMaterial color="#e7e8e2" metalness={.72} roughness={.27}/></mesh>
 <mesh rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.035,.035,3.1,10]}/><meshStandardMaterial color="#a7c2cd" metalness={.7} roughness={.3}/></mesh>
 {[-1,1].map(side=><group key={side} position={[side*1.05,0,0]}>
  <mesh><boxGeometry args={[1.15,.055,.8]}/><meshStandardMaterial color="#173c52" metalness={.55} roughness={.26}/></mesh>
  {[-.38,0,.38].map(x=><mesh key={x} position={[x,.034,0]}><boxGeometry args={[.016,.01,.75]}/><meshBasicMaterial color={C.blue}/></mesh>)}
  <mesh position={[0,.034,0]}><boxGeometry args={[1.1,.01,.018]}/><meshBasicMaterial color={C.blue}/></mesh>
 </group>)}
 <mesh position={[0,-.4,0]} rotation={[Math.PI,0,0]}><coneGeometry args={[.27,.24,24,1,true]}/><meshStandardMaterial color="#e2e7e8" side={DoubleSide} metalness={.6} roughness={.2}/></mesh>
 <mesh position={[0,-.59,0]}><sphereGeometry args={[.07,12,8]}/><meshBasicMaterial color={C.blue}/></mesh>
 </group>;}

function World({t,expandTeam=true,sameAgentPings=false}:{t:number;expandTeam?:boolean;sameAgentPings?:boolean}){
 const connected=t>=23,flight=t>=27;
 const states=[0,1].map(i=>flight?airborne(t,i,sameAgentPings?29.4:27):baseline(connected?5:t,i));
 const paths=[0,1].map(i=>{const arr:Vector3[]=[];const start=flight?27:5;const end=flight?t:Math.min(t,23);for(let s=start;s<=end;s+=.10)arr.push((flight?airborne(s,i,sameAgentPings?29.4:27):baseline(s,i)).pos);if(end>=start)arr.push(states[i].pos);return arr;});
 const message=(sameAgentPings?[[27,29.4],...windows]:windows).find(([a,b])=>t>=a&&t<b);
 const hub=sat(t).add(new Vector3(0,-.45,0));
 const peers=states.map(s=>s.pos);
 const landed=!connected&&states[0].landed&&t>=8&&t<20;
 const roundTrip=Boolean(message&&sameAgentPings);
 const route=message&&!roundTrip?[peers[1],hub,peers[0],hub,peers[1]]:landed?[peers[1],peers[0],peers[1]]:null;
 let pulse:Vector3|undefined;
 if(route){const f=message?clamp((t-message[0])/(message[1]-message[0])):((t-ends[states[0].leg])/2.4)%1;const k=Math.min(route.length-2,Math.floor(f*(route.length-1)));pulse=route[k].clone().lerp(route[k+1],f*(route.length-1)-k);}
 // Both agents report concurrently; each response follows its own route home.
 const progress=message?clamp((t-message[0])/(message[1]-message[0])):0;
 const travel=progress<.5?progress*2:(1-progress)*2;
 return <>
  <Camera t={t}/><color attach="background" args={[C.bg]}/><fog attach="fog" args={[C.bg,24,48]}/>
  <ambientLight intensity={.7}/><hemisphereLight args={['#b8dff5','#25313c',1.6]}/>
  <directionalLight position={[-4,12,5]} intensity={3.5} color="#daf5ff" castShadow shadow-mapSize={[1024,1024]} shadow-camera-left={-12} shadow-camera-right={12} shadow-camera-top={10} shadow-camera-bottom={-10}/>
  <pointLight position={[3,5,-4]} intensity={65} color={C.blue}/>
  <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.06,0]} receiveShadow><planeGeometry args={[120,120]}/><meshStandardMaterial color={C.floor} roughness={.76} metalness={.15}/></mesh>
  <GoalMarker/>
  <gridHelper args={[28,28,'#1a2e3f','#152332']} position={[0,-.05,0]}/>
  {[0,1].map(i=><React.Fragment key={i}><Pad x={-7} z={i?.85:-.85} color={i?C.white:C.blue}/>{t>=48&&<Pad x={GOAL_X} z={i?.85:-.85} color={i?C.white:C.blue} active/>}</React.Fragment>)}
  {!connected&&[0,1,2,3].map(stop=>[0,1].map(i=><LandingMark key={`${stop}-${i}`} t={t} stop={stop} i={i}/>))}
  <Clouds t={connected?t-23:t} frontier={states[0].pos.x}/>
  {!connected&&paths.map((ps,i)=>ps.length>1&&<Tube key={i} points={ps} color={i?C.white:C.blue} opacity={.65}/>)}
  {!connected&&[1,2,3].map(leg=>[0,1].map(i=>{
   const from=starts[leg],to=Math.min(t,from+(ends[leg]-from)*.28);
   if(to<=from)return null;
   const ps=Array.from({length:30},(_,k)=>baseline(mix(from,to,k/29),i).pos);
   return <Tube key={`rework-${leg}-${i}`} points={ps} color={C.amber} radius={.025} opacity={.95}/>;
  }))}
  {flight&&paths.map((ps,i)=>ps.length>1&&<Tube key={i} points={ps} color={i?C.white:C.blue} opacity={.8}/>)}
  {states.map((s,i)=><group key={i} position={s.pos} rotation={[s.bank,s.yaw,0]}><Plane color={s.reworking?C.amber:i?C.white:C.blue}/></group>)}
  {connected&&<Satellite t={t}/>}
  {expandTeam&&<ExtraAgents t={t} sameAgentPings={sameAgentPings}/>}
  {route&&<><Tube points={message?[peers[0],hub]:peers} color={C.blue} radius={.009} opacity={.24}/>{message&&<Tube points={[peers[1],hub]} color={C.blue} radius={.009} opacity={.24}/>}<mesh position={pulse}><sphereGeometry args={[.065,10,8]}/><meshBasicMaterial color={C.blue}/></mesh></>}
  {roundTrip&&peers.map((peer,i)=><React.Fragment key={`check-in-${i}`}>
   <Tube points={[peer,hub]} color={i?C.white:C.blue} radius={.009} opacity={.3}/>
   <mesh position={peer.clone().lerp(hub,travel)}><sphereGeometry args={[.075,10,8]}/><meshBasicMaterial color={i?C.white:C.blue}/></mesh>
  </React.Fragment>)}
 </>;
}

const Label:React.FC<{p:Vector3;t:number;children:React.ReactNode;color?:string}>=({p,t,children,color=C.muted})=>{const expand=React.useContext(CameraMode),v=p.clone().project(sceneCamera(t,expand)),q={left:(v.x+1)*960,top:(1-v.y)*540};return <div style={{position:'absolute',left:q.left,top:q.top,transform:'translate(-50%,-50%)',fontSize:19,letterSpacing:2,color,whiteSpace:'nowrap'}}>{children}</div>;};
export const FlightSequence:React.FC<{timeOffset?:number;expandTeam?:boolean;sameAgentPings?:boolean;goalLabel?:string;overlays?:boolean;audioVolume?:number;timeScale?:number;headlineOverride?:string;headlineCentered?:boolean;headlineOpacity?:number;headlineLift?:number;sceneVeil?:number;agentLabelsOpacity?:number}>=({timeOffset=0,expandTeam=true,sameAgentPings=false,goalLabel="Project goal",overlays=true,audioVolume=1,timeScale=1,headlineOverride,headlineCentered=false,headlineOpacity=1,headlineLift=0,sceneVeil=0,agentLabelsOpacity=1})=>{
 const frame=useCurrentFrame(),t=frame/FPS*timeScale+timeOffset,{width,height}=useVideoConfig();const words=expandTeam&&t>=SCALE_AT?{title:t<SCALE_AT+12?'Now imagine coordinating 10 agents.':'More prework. Less rework.'}:copy(t);
 const connected=t>=23,states=[0,1].map(i=>t>=27?airborne(t,i,sameAgentPings?29.4:27):baseline(connected?5:t,i));
 const intro=ease(t/.8);const transition=t>=23&&t<27?Math.sin(clamp((t-23)/4)*Math.PI)*.12:0;
 return <CameraMode.Provider value={expandTeam}><AbsoluteFill style={{background:C.bg,fontFamily:'Inter Variable, sans-serif',color:C.white}}>
  <Audio src={staticFile('audio/soundtrack.wav')} startFrom={Math.round(timeOffset*FPS)} playbackRate={timeScale} volume={f=>audioVolume*.8*(1-ease((f/FPS-51.5)/2))}/>
  <ThreeCanvas width={width} height={height} shadows dpr={1} camera={{fov:42,position:[0,10.5,18]}} gl={{antialias:true,alpha:false,powerPreference:'high-performance'}}><World t={t} expandTeam={expandTeam} sameAgentPings={sameAgentPings}/></ThreeCanvas>
  <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(8,14,22,.96) 0%,rgba(8,14,22,.15) 30%,rgba(8,14,22,0) 62%,rgba(8,14,22,.94) 88%)',pointerEvents:'none'}}/>
  <div style={{position:'absolute',inset:0,background:C.blue,opacity:transition*(1-sceneVeil),pointerEvents:'none'}}/>
  <AbsoluteFill style={{background:C.bg,opacity:sceneVeil,pointerEvents:'none'}}/>
  <AbsoluteFill style={{opacity:overlays?ease((t-4)/1):0,pointerEvents:'none'}}>
  <div style={{position:'absolute',top:headlineCentered?'50%':125,left:90,right:90,opacity:intro*headlineOpacity,textAlign:headlineCentered?'center':'left',transform:headlineCentered?`translateY(calc(-50% + ${headlineLift}px))`:`translateY(${(1-intro)*16+headlineLift}px)`}}>
   <div style={{fontSize:headlineOverride?58:t>=49?68:58,fontWeight:450,letterSpacing:-2.1,lineHeight:1.12}}>{headlineOverride??words.title}</div>
  </div>
  <AbsoluteFill style={{opacity:1-sceneVeil}}>
  {t>=5&&goalLabel&&<Label t={t} p={new Vector3(GOAL_X,3.9,0)} color={C.white}>{goalLabel}</Label>}
  {connected&&<div style={{opacity:ease((t-24)/.8)}}><Label t={t} p={sat(t).add(new Vector3(0,.65+(1-ease((t-23)/2))*5,0))} color={C.blue}>Midflight</Label></div>}
  {!connected&&ends.map((at,j)=>t>=at&&[0,1].map(i=><Label key={`${j}-${i}`} t={t} p={baseline(at+.01,i).pos.clone().add(new Vector3(0,-.15,.38))} color={C.muted}>Commit {j+1}</Label>))}
  {t>=5&&<div style={{opacity:agentLabelsOpacity}}><Label t={t} p={states[0].pos.clone().add(new Vector3(0,1,0))} color={C.blue}>Agent A</Label><Label t={t} p={states[1].pos.clone().add(new Vector3(0,1,0))} color={C.white}>Agent B</Label></div>}
  {expandTeam&&t>=SCALE_AT&&Array.from({length:8},(_,j)=>{
   const i=j+2,local=t-SCALE_AT,show=ease((local-1.2-j*.3)/.9);
   return <div key={i} style={{opacity:show*.8}}><Label t={t} p={extraPosition(local,i).add(new Vector3(0,.75,0))} color={i%2?C.white:C.blue}>Agent {String.fromCharCode(65+i)}</Label></div>;
  })}
  </AbsoluteFill>
  </AbsoluteFill>
 </AbsoluteFill></CameraMode.Provider>;
};

// Expansion uses the original world and clock; only the camera widens.
const SCALE_AT=37.5;
function sceneCamera(t:number,expand=true){
 if(!expand||t<=SCALE_AT)return cameraAt(t);
 const c=cameraAt(SCALE_AT),pull=ease((t-SCALE_AT)/5);
 c.position.lerp(new Vector3(1.5,17,25),pull);
 c.lookAt(0,mix(1.25,1.5,pull),0);c.updateProjectionMatrix();c.updateMatrixWorld();return c;
}
function extraPosition(t:number,i:number){
 const j=i-2,row=Math.floor(j/2),col=j%2;
 return new Vector3((col? -3:-7)+t*.42,1.35+Math.sin(t*.55+i*.8)*.16,[-6,-3,3,6][row]+Math.sin(t*.7+i*.9)*.3);
}
function ExtraAgents({t,sameAgentPings=false}:{t:number;sameAgentPings?:boolean}){
 const local=t-SCALE_AT;
 if(local<0)return null;
 const anchor=sat(t).add(new Vector3(0,-.45,0));
 return <>{Array.from({length:8},(_,j)=>{
  const i=j+2,appear=1.2+j*.3,show=ease((local-appear)/.9);
  if(show<=0)return null;
  const color=i%2?C.white:C.blue,p=extraPosition(local,i);
  const trail=Array.from({length:35},(_,k)=>extraPosition(local-3.4+k*.1,i));
  const start=sameAgentPings?4+Math.floor(j/2)*1.4+(j%2)*.12:4+j*1.4,duration=sameAgentPings?2:1,active=local>=start&&local<start+duration;
  const progress=clamp((local-start)/duration);
  const travel=sameAgentPings?(progress<.5?progress*2:(1-progress)*2):progress;
  const pulse=p.clone().lerp(anchor,travel);
  return <React.Fragment key={i}>
   <group position={p} rotation={[Math.sin(local*.7+i)*.09,0,0]} scale={show}><Plane color={color}/></group>
   <Tube points={trail} color={color} radius={.012} opacity={show*.43}/>
   {active&&<><Tube points={[p,anchor]} color={sameAgentPings?color:C.blue} radius={.008} opacity={show*.16}/>
    <mesh position={pulse}><sphereGeometry args={[.062,8,8]}/><meshBasicMaterial color={sameAgentPings?color:C.blue}/></mesh></>}
  </React.Fragment>;
 })}</>;
}
export const FlightFilm:React.FC=()=> <AbsoluteFill style={{background:C.bg}}>
 <Sequence from={FLIGHT_OFFSET*FPS}><FlightSequence/></Sequence>
 <Sequence durationInFrames={OPENING_SECONDS*FPS}><ProblemOpening/></Sequence>
</AbsoluteFill>;
