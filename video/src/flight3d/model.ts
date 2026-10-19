import {PerspectiveCamera, Vector3} from 'three';
export const FPS=30, FLIGHT_OFFSET=20, OPENING_SECONDS=25, SECONDS=53.5+FLIGHT_OFFSET;
export const C={bg:'#080e16',floor:'#101a27',blue:'#72d6ee',white:'#f2ede1',muted:'#94a6b6',amber:'#ffb080'};
export const clamp=(x:number)=>Math.max(0,Math.min(1,x));
export const ease=(x:number)=>{x=clamp(x);return x*x*(3-2*x);};
export const mix=(a:number,b:number,p:number)=>a+(b-a)*p;
export const starts=[5,10,15,20],ends=[8,13,18,24];
export const GOAL_X=11.5;
const px=[-7,-3.4,.4,3.8,GOAL_X],pz=[0,-2.8,2,-1.5,0];
export function baseline(t:number,i:number){
 let leg=0;while(leg<3&&t>=starts[leg+1])leg++;
 const u=clamp((t-starts[leg])/(ends[leg]-starts[leg]));
 // After a commit, spend part of the next flight retracing completed work.
 const reworking=leg>0&&u>0&&u<.28;
 const p=leg===0?ease(u):u<.28?-.27*ease(u/.28):mix(-.27,1,ease((u-.28)/.72));
 const side=i?-1:1;
 const pos=new Vector3(mix(px[leg],px[leg+1],p),.28+1.45*Math.pow(Math.max(0,Math.sin(Math.PI*u)),.7),mix(pz[leg],pz[leg+1],p)*side+(i?.85:-.85));
 const turn=leg>0?Math.PI*(1-ease((u-.20)/.16)):0;
 return {pos,leg,reworking,landed:t>=ends[leg]||t<5,yaw:-Math.atan2((pz[leg+1]-pz[leg])*side,px[leg+1]-px[leg])+turn,bank:Math.sin(u*Math.PI)*side*.12};
}
export function airborne(t:number,i:number,launchAt=27){
 const p=clamp((t-launchAt)/(48-launchAt)),side=i?1:-1;
 const z=side*(Math.sin(Math.PI*p)*(1.8+.25*Math.sin(p*Math.PI*6)))+(i?.85:-.85);
 const y=.28+1.55*Math.min(ease(p/.12),ease((1-p)/.12));
 const pos=new Vector3(mix(-7,GOAL_X,p),y,z);
 const dz=side*(Math.PI*Math.cos(Math.PI*p)*(1.8+.25*Math.sin(p*Math.PI*6))+Math.sin(Math.PI*p)*1.5*Math.PI*Math.cos(p*Math.PI*6));
 return {pos,leg:0,reworking:false,landed:p===0||p===1,yaw:-Math.atan2(dz,GOAL_X+7),bank:-side*.22*Math.sin(p*Math.PI*6)};
}
export function sat(t:number){const a=(t-23)*.075;return new Vector3(Math.sin(a)*1.6,4.1+Math.sin(a*.7)*.2,-1.6+Math.cos(a)*.5);}
export function cameraAt(t:number){
 const a=-.12+.22*ease(t/54);const zoom=t<5?mix(1.08,1,ease(t/5)):1;
 const camera=new PerspectiveCamera(42,1920/1080,.1,100);
 camera.position.set(Math.sin(a)*18,10.5*zoom,Math.cos(a)*18*zoom);camera.lookAt(0,1.25,0);camera.updateProjectionMatrix();camera.updateMatrixWorld();return camera;
}
export function project(p:Vector3,t:number){const v=p.clone().project(cameraAt(t));return {left:(v.x+1)*960,top:(1-v.y)*540};}
export const windows=[[31,33.4],[37,39.4],[43,45.4]];
export function copy(t:number):{title:string}{
 if(t<5)return {title:'Same brief. Separate work.'};
 if(t<8)return {title:'Commit. Discover. Rework.'};
 if(t<10)return {title:'Commit. Discover. Rework.'};
 if(t<13)return {title:'Rework means going back.'};
 if(t<15)return {title:'Commit. Discover. Rework.'};
 if(t<18)return {title:'Rework means going back.'};
 if(t<20)return {title:'Commit. Discover. Rework.'};
 if(t<23)return {title:'Repeated commits. Time lost to rework.'};
 if(t<27)return {title:'Meet Midflight.'};
 if(t<33.5)return {title:'Share context. Adjust. Commit.'};
 if(t<39.8)return {title:'Prework avoids the next detour.'};
 if(t<45.8)return {title:'Separate agents. Shared direction.'};
 if(t<49)return {title:'The work arrives already aligned.'};
 return {title:'More prework. Less rework.'};
}
