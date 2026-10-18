import React,{useMemo} from 'react';
import {CanvasTexture,SRGBColorSpace} from 'three';
import {ease} from './model';

// A deterministic, code-painted smoke texture. The billboards occupy a 3D
// volume, so the camera sees parallax between cloud banks and individual puffs.
function cloudTexture(){
 const size=192,canvas=document.createElement('canvas');canvas.width=canvas.height=size;
 const context=canvas.getContext('2d')!;const image=context.createImageData(size,size);
 const hash=(x:number,y:number)=>{const n=Math.sin(x*127.1+y*311.7)*43758.5453;return n-Math.floor(n);};
 const noise=(x:number,y:number)=>{const ix=Math.floor(x),iy=Math.floor(y),fx=ease(x-ix),fy=ease(y-iy);return (hash(ix,iy)*(1-fx)+hash(ix+1,iy)*fx)*(1-fy)+(hash(ix,iy+1)*(1-fx)+hash(ix+1,iy+1)*fx)*fy;};
 for(let y=0;y<size;y++)for(let x=0;x<size;x++){
  const u=x/(size-1)*2-1,v=y/(size-1)*2-1;
  const n=noise(u*3+8,v*3+8)*.60+noise(u*7+20,v*7+20)*.27+noise(u*15+40,v*15+40)*.13;
  const radius=Math.sqrt(u*u+v*v),edge=ease((1-radius+(n-.5)*.20)/.46);
  const alpha=edge*(.70+.30*n)*.75;
  const light=.66+(1-(v+1)/2)*.28+n*.09,index=(y*size+x)*4;
  image.data[index]=Math.round(142*light);image.data[index+1]=Math.round(166*light);image.data[index+2]=Math.round(185*light);image.data[index+3]=Math.round(alpha*255);
 }
 context.putImageData(image,0,0);const texture=new CanvasTexture(canvas);texture.colorSpace=SRGBColorSpace;return texture;
}

const banks=[
 [-3.6,-4.4],[-2.4,.1],[-2.8,4.5],[.1,-4.8],[.4,-.4],[.6,4.2],
 [3.6,-4.3],[3.2,.1],[3.8,4.7],[6.5,-4.6],[6.7,-.2],[7,4.4],[9.5,-2],[9.7,3],
];
const puffs=[[-.8,.1,0,3.9,2.0],[.5,.35,.3,4.5,2.6],[1.1,-.05,-.4,3.4,1.8],[-.1,.7,-.3,3.3,2.4],[-.2,-.35,.8,4.3,1.5]];

export function Clouds({t,frontier}:{t:number;frontier:number}){
 const texture=useMemo(cloudTexture,[]);
 return <group>
  {banks.map(([x,z],bank)=>{
   // Only the space already explored becomes clearer. The satellite does not
   // remove uncertainty ahead: both versions retain the same cloud field.
   const ahead=ease((x-frontier+.3)/3.2),opacity=.10+.70*ahead;
   const drift=Math.sin(t*.07+bank*.9)*.15;
   return <group key={bank} position={[x,1.35,z+drift]}>
    {puffs.map(([dx,dy,dz,w,h],i)=><sprite key={i} position={[dx,dy,dz]} scale={[w,h,1]}>
     <spriteMaterial map={texture} transparent opacity={opacity} depthWrite={false} toneMapped={false} rotation={(bank%3-1)*.09}/>
    </sprite>)}
   </group>;
  })}
 </group>;
}
