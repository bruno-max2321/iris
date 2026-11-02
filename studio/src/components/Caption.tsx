import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {loadFont} from '@remotion/google-fonts/LibreBaskerville';
import {Cue} from '../spec';
import {CAPTION_Y, CaptionLook, FPS, H, LOOKS} from '../style';

const {fontFamily} = loadFont('normal', {weights: ['400'], subsets: ['latin']});
loadFont('italic', {weights: ['400'], subsets: ['latin']});

// One caption cue. The references cut captions on and off with the voice; the label wipes in from the left
// (Bethlem), the box pops (Otis), bare text just appears (Santos).
export const Caption: React.FC<{cue: Cue; look: CaptionLook}> = ({cue, look}) => {
	const f = useCurrentFrame(); // frames since the cue started
	const L = LOOKS[cue.look ?? look];
	const enterFrames = 3;
	const reveal = L.enter === 'wipe' ? interpolate(f, [0, enterFrames], [100, 0], {extrapolateRight: 'clamp'}) : 0;
	const pop = L.enter === 'pop' ? interpolate(f, [0, enterFrames], [0.92, 1], {extrapolateRight: 'clamp'}) : 1;
	const fade = L.enter === 'pop' ? interpolate(f, [0, 2], [0, 1], {extrapolateRight: 'clamp'}) : 1;
	const textOn = L.enter !== 'wipe' || f >= 1;
	return (
		<div style={{position: 'absolute', left: 0, right: 0, top: (cue.y ?? CAPTION_Y) * H, display: 'flex', justifyContent: 'center', transform: 'translateY(-50%)'}}>
			<span style={{
				fontFamily, fontStyle: L.italic ? 'italic' : 'normal', fontSize: L.size, lineHeight: 1.2, letterSpacing: -0.3,
				color: textOn ? L.color : 'transparent', backgroundColor: L.background, padding: L.padding, textShadow: L.shadow,
				clipPath: `inset(0 ${reveal}% 0 0)`, transform: `scale(${pop})`, opacity: fade, whiteSpace: 'nowrap',
			}}>
				{cue.text}
			</span>
		</div>
	);
};

export const cueFrames = (cue: Cue) => ({from: Math.round(cue.atS * FPS), frames: Math.max(1, Math.round(cue.holdS * FPS))});
