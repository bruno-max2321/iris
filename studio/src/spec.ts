import {BANDS, CAMERA_MIX, CaptionLook, Grade, Move, NEVER} from './style';

// A reel is a list of shots, each a collage of layers that the camera moves over, plus the voice-over and
// the caption cues on their own timeline (captions are short, 1-3 words, and do not follow the cuts).
export type Layer = {
	src: string;          // file under public/
	x: number; y: number; // centre, share of frame width / height
	w: number;            // width, share of frame width
	rotate?: number;      // degrees
	depth?: number;       // 0 = back plate, 1 = front cut-out; nearer layers move more (parallax)
	shadow?: boolean;     // cut-out drop shadow
};

export type Shot = {
	durationS: number;
	move: Move;
	layers: Layer[];
	transitionIn?: 'cut' | 'glitch' | 'flash';
};

export type Cue = {text: string; atS: number; holdS: number; look?: CaptionLook; y?: number};

export type ReelSpec = {
	title: string;
	grade: Grade;
	look: CaptionLook;    // one caption look per video
	background: string;   // colour behind the plates
	shots: Shot[];
	cues: Cue[];
	audio: {src: string; atS: number}[];
};

export type Issue = {level: 'error' | 'warn'; message: string};

// The style's limits checked before rendering; iris check measures the rendered file afterwards.
export const checkSpec = (spec: ReelSpec): Issue[] => {
	const out: Issue[] = [];
	const total = spec.shots.reduce((s, x) => s + x.durationS, 0);
	spec.shots.forEach((s, i) => {
		if ((NEVER as readonly string[]).includes(s.move)) out.push({level: 'error', message: `shot ${i + 1}: ${s.move} is prohibited`});
		if (s.durationS > BANDS.shotS.hardMax) out.push({level: 'error', message: `shot ${i + 1} lasts ${s.durationS}s, over ${BANDS.shotS.hardMax}s`});
		if (!s.layers.length) out.push({level: 'error', message: `shot ${i + 1} has no layers`});
	});
	const rate = total > 0 ? (spec.shots.length - 1) / total : 0;
	if (rate < BANDS.cutsPerS.min || rate > BANDS.cutsPerS.max) {
		out.push({level: 'warn', message: `cut rate ${rate.toFixed(3)}/s is outside [${BANDS.cutsPerS.min}, ${BANDS.cutsPerS.max}]`});
	}
	spec.cues.forEach((c) => {
		const words = c.text.trim().split(/\s+/).length;
		if (words > BANDS.captionMaxWords) out.push({level: 'warn', message: `caption "${c.text}" has ${words} words, the style shows at most ${BANDS.captionMaxWords}`});
		if (c.holdS * 1000 > BANDS.captionHoldMs.max) out.push({level: 'warn', message: `caption "${c.text}" holds ${c.holdS}s`});
	});
	if (spec.cues.length && spec.cues[0].atS > BANDS.firstTextS.max) out.push({level: 'warn', message: `first caption at ${spec.cues[0].atS}s, the style shows text by ${BANDS.firstTextS.max}s`});
	const time: Record<string, number> = {};
	spec.shots.forEach((s) => {time[s.move] = (time[s.move] ?? 0) + s.durationS;});
	(Object.keys(CAMERA_MIX) as Move[]).forEach((m) => {
		const share = (time[m] ?? 0) / total;
		if (Math.abs(share - CAMERA_MIX[m]) > 0.2) out.push({level: 'warn', message: `${m} covers ${Math.round(100 * share)}% of screen time, the style ${Math.round(100 * CAMERA_MIX[m])}%`});
	});
	return out;
};

export const totalSeconds = (spec: ReelSpec) => spec.shots.reduce((s, x) => s + x.durationS, 0);
