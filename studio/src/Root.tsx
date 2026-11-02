import React from 'react';
import {Composition} from 'remotion';
import sample from '../reels/sample-calorico.json';
import {Reel} from './Reel';
import {ReelSpec, checkSpec, totalSeconds} from './spec';
import {FPS, H, W} from './style';

export const Root: React.FC = () => (
	<Composition
		id="Reel"
		component={Reel}
		width={W}
		height={H}
		fps={FPS}
		durationInFrames={1}
		defaultProps={sample as ReelSpec}
		calculateMetadata={({props}) => {
			const issues = checkSpec(props);
			issues.filter((i) => i.level === 'warn').forEach((i) => console.warn(`[style] ${i.message}`));
			const errors = issues.filter((i) => i.level === 'error');
			if (errors.length) throw new Error(`reel breaks the style: ${errors.map((e) => e.message).join('; ')}`);
			return {durationInFrames: Math.round(totalSeconds(props) * FPS)};
		}}
	/>
);
