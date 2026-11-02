import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';

export const GLITCH_FRAMES = 3;

// The RGB-split glitch of the references (Otis cuts through a red/cyan tear): for the first frames of the
// shot the red and cyan channels separate, a few bands slip sideways, and it settles into the clean picture.
export const Glitch: React.FC<{id: string; children: React.ReactNode}> = ({id, children}) => {
	const f = useCurrentFrame();
	if (f >= GLITCH_FRAMES) return <>{children}</>;
	const k = 1 - f / GLITCH_FRAMES;
	const dx = Math.round(26 * k);
	const fid = `${id}-${f}`;
	const bands = [0, 1].map((b) => {
		const top = Math.floor(random(`${fid}-t${b}`) * 85);
		return {top, height: 4 + Math.floor(random(`${fid}-h${b}`) * 10), shift: Math.round((random(`${fid}-s${b}`) - 0.5) * 70 * k)};
	});
	return (
		<AbsoluteFill>
			<svg width={0} height={0} style={{position: 'absolute'}}>
				<filter id={fid} x="-5%" y="0" width="110%" height="100%" colorInterpolationFilters="sRGB">
					<feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
					<feOffset in="r" dx={dx} dy={0} result="ro" />
					<feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" result="gb" />
					<feOffset in="gb" dx={-dx} dy={0} result="gbo" />
					<feBlend in="ro" in2="gbo" mode="screen" />
				</filter>
			</svg>
			<AbsoluteFill style={{filter: `url(#${fid})`}}>{children}</AbsoluteFill>
			{bands.map((b, i) => (
				<AbsoluteFill key={i} style={{clipPath: `inset(${b.top}% 0 ${100 - b.top - b.height}% 0)`, transform: `translateX(${b.shift}px)`, filter: `url(#${fid})`}}>
					{children}
				</AbsoluteFill>
			))}
			<AbsoluteFill style={{backgroundColor: f % 2 ? '#00E0C0' : '#FF2A1A', mixBlendMode: 'color', opacity: 0.18 * k}} />
		</AbsoluteFill>
	);
};

// A two-to-three frame flash toward paper white (the picture shows through, so the cut stays readable), the other hard transition of the references.
export const Flash: React.FC<{children: React.ReactNode}> = ({children}) => {
	const f = useCurrentFrame();
	return (
		<AbsoluteFill>
			{children}
			{f < 3 ? <AbsoluteFill style={{backgroundColor: '#F4EEDF', opacity: [0.6, 0.3, 0.1][f]}} /> : null}
		</AbsoluteFill>
	);
};
