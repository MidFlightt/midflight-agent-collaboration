import React from 'react';
import {Composition, registerRoot} from 'remotion';
import '@fontsource-variable/inter';
import {Pitch, PITCH_FRAMES} from './combined-story/Pitch';
import {ReorderedOpening, REORDERED_OPENING_FRAMES} from './combined-story/ReorderedOpening';

registerRoot(() => <>
  <Composition id="MidflightPitch" component={Pitch} width={1920} height={1080} fps={30} durationInFrames={PITCH_FRAMES}/>
  <Composition id="Opening" component={ReorderedOpening} width={1920} height={1080} fps={30} durationInFrames={REORDERED_OPENING_FRAMES}/>
</>);
