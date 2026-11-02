import React from 'react';
import {AbsoluteFill, Img, random, staticFile, useCurrentFrame} from 'remotion';
import {GRADES, Grade as GradeName} from '../style';

export const GRAIN_TILES = 6;

// The archival print look applied to the pictures (not the captions): colour grade and tint, a slight
// gate weave and exposure flicker from frame to frame.
export const Graded: React.FC<{grade: GradeName; children: React.ReactNode}> = ({grade, children}) => {
	const f = useCurrentFrame();
	const g = GRADES[grade];
	const wx = (random(`wx${f}`) - 0.5) * 1.6;
	const wy = (random(`wy${f}`) - 0.5) * 1.6;
	const flicker = 0.99 + random(`fl${f}`) * 0.015; // stronger flicker swamps the cuts (Iris reads it as constant change)
	return (
		<AbsoluteFill style={{filter: `${g.filter} brightness(${flicker.toFixed(3)})`}}>
			<AbsoluteFill style={{transform: `translate(${wx}px, ${wy}px) scale(1.006)`}}>{children}</AbsoluteFill>
			<AbsoluteFill style={{backgroundColor: g.tint, mixBlendMode: 'soft-light', opacity: g.tintOpacity * 3}} />
		</AbsoluteFill>
	);
};

// Film grain and vignette over everything, captions included, as in the references.
export const FilmSurface: React.FC = () => {
	const f = useCurrentFrame();
	return (
		<AbsoluteFill style={{pointerEvents: 'none'}}>
			<Img src={staticFile(`gen/grain_${f % GRAIN_TILES}.png`)} style={{width: '100%', height: '100%', mixBlendMode: 'overlay', opacity: 0.28}} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 48%, rgba(0,0,0,0) 55%, rgba(18,10,4,0.42) 100%)'}} />
		</AbsoluteFill>
	);
};
