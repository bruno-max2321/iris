import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Shot} from '../spec';
import {FPS, H, MOVE_RATE, W} from '../style';

// A steady Ken Burns drift, as in the references: nearly constant speed from the first frame of the shot.
// (An ease-out that moves most at the cut blurs the cut itself: Iris then misses it, and so does the eye.)
const ease = Easing.bezier(0.3, 0.12, 0.7, 0.88);

export const camera = (shot: Shot, frame: number) => {
	const frames = Math.max(1, Math.round(shot.durationS * FPS) - 1);
	const p = interpolate(frame, [0, frames], [0, 1], {easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const zoom = Math.min(MOVE_RATE.scaleMax, MOVE_RATE.scalePerS * shot.durationS + 0.04);
	const shift = Math.min(MOVE_RATE.shiftMax, MOVE_RATE.shiftPerS * shot.durationS + 0.02);
	switch (shot.move) {
		case 'pull_out': return {scale: 1 + zoom * (1 - p), dx: 0, dy: 0};
		case 'push_in': return {scale: 1 + zoom * p, dx: 0, dy: 0};
		case 'tilt_down': return {scale: 1, dx: 0, dy: (0.5 - p) * shift * H};
		case 'pan_right': return {scale: 1, dx: (0.5 - p) * shift * W, dy: 0};
	}
};

export const Collage: React.FC<{shot: Shot; background: string}> = ({shot, background}) => {
	const f = useCurrentFrame();
	const cam = camera(shot, f);
	return (
		<AbsoluteFill style={{backgroundColor: background, overflow: 'hidden'}}>
			{shot.layers.map((l, i) => {
				const depth = l.depth ?? (i === 0 ? 0 : 1);
				const k = 0.6 + 0.8 * depth; // parallax: the front cut-outs travel further than the back plate
				const s = 1 + (cam.scale - 1) * k;
				const drift = depth > 0 ? 5 * Math.sin(f / 19 + i * 1.7) : 0;
				return (
					<AbsoluteFill key={i} style={{transform: `translate(${cam.dx * k}px, ${cam.dy * k + drift}px) scale(${s})`}}>
						<Img
							src={staticFile(l.src)}
							style={{
								position: 'absolute', left: l.x * W, top: l.y * H, width: l.w * W,
								transform: `translate(-50%, -50%) rotate(${l.rotate ?? 0}deg)`,
								filter: l.shadow ? 'drop-shadow(0 22px 26px rgba(20, 12, 4, 0.5))' : undefined,
							}}
						/>
					</AbsoluteFill>
				);
			})}
		</AbsoluteFill>
	);
};
