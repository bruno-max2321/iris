import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {Caption, cueFrames} from './components/Caption';
import {Collage} from './components/Collage';
import {FilmSurface, Graded} from './components/Grade';
import {Flash, Glitch} from './components/Transition';
import {ReelSpec} from './spec';
import {FPS} from './style';

export const shotStarts = (spec: ReelSpec) => {
	let t = 0;
	return spec.shots.map((s) => {
		const from = Math.round(t * FPS);
		t += s.durationS;
		return {from, frames: Math.round(t * FPS) - from};
	});
};

export const Reel: React.FC<ReelSpec> = (spec) => {
	const starts = shotStarts(spec);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<Graded grade={spec.grade}>
				{spec.shots.map((shot, i) => {
					const body = <Collage shot={shot} background={spec.background} />;
					return (
						<Sequence key={i} from={starts[i].from} durationInFrames={starts[i].frames} name={`shot ${i + 1} ${shot.move}`}>
							{shot.transitionIn === 'glitch' ? <Glitch id={`g${i}`}>{body}</Glitch> : shot.transitionIn === 'flash' ? <Flash>{body}</Flash> : body}
						</Sequence>
					);
				})}
			</Graded>
			{spec.cues.map((cue, i) => {
				const c = cueFrames(cue);
				return (
					<Sequence key={`c${i}`} from={c.from} durationInFrames={c.frames} name={`"${cue.text}"`}>
						<Caption cue={cue} look={spec.look} />
					</Sequence>
				);
			})}
			<FilmSurface />
			{spec.audio.map((a, i) => (
				<Sequence key={`a${i}`} from={Math.round(a.atS * FPS)}>
					<Audio src={staticFile(a.src)} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};
