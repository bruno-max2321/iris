// The numbers of Style Bible archival-motion-v1, approved 2026-11-02 (sha256 0bc678dfdb9a…), built from
// ref_308c466f03ac (Otis), ref_dc8b2879f7db (Santos/Cartier) and ref_7820b5fdf7f2 (Bethlem).
// The measured bands come from the Bible; the looks (colours of the caption labels, grade, glitch) are read
// from the style board screenshots, because the Bible does not measure them (or, for the yellow label of
// ref_7820, measures it wrong: see the Phase 2 note in README.md).

export const STYLE_ID = 'archival-motion-v1';
export const BIBLE_SHA256 = '0bc678dfdb9a535164822356bcc38879eada15d0d3d68ff36d3c8376dff5fb31';

export const W = 1080;
export const H = 1920;
export const FPS = 24;

export const BANDS = {
	cutsPerS: {min: 0.625, max: 0.95, typical: 0.814},
	shotS: {p25: 0.417, p50: 0.917, p75: 1.737, max: 5.58, hardMax: 7.26},
	hookCutsPerS: {min: 0.333, max: 1, typical: 0.667},
	firstTextS: {max: 1.2, typical: 0.25},
	captionHoldMs: {min: 42, max: 1347, typical: 467},
	captionMaxWords: 3,
	loudnessLufs: {min: -15.1, max: -13.1, target: -14},
	truePeakDbtp: -1.5, // the Bible allows up to 0.9; platforms clip above -1
};

// share of screen time per camera movement in the references (static is prohibited by the brief)
export const CAMERA_MIX = {pull_out: 0.533, tilt_down: 0.24, pan_right: 0.125, push_in: 0.102} as const;
export type Move = keyof typeof CAMERA_MIX;
export const NEVER = ['static', 'whip_pan', 'wipe', 'cross_dissolve'] as const;

// How far each move travels per second of shot, and the cap for long shots. A pull out starts close and
// settles; a tilt down slides the picture up; a pan right slides it left.
export const MOVE_RATE = {scalePerS: 0.11, scaleMax: 0.22, shiftPerS: 0.07, shiftMax: 0.16}; // shift: share of frame size

export type CaptionLook = 'label' | 'box' | 'plain' | 'plain_light';

// The three caption looks of the references, one per video (the Bible keeps them as allowed variants).
export const LOOKS: Record<CaptionLook, {
	color: string; background?: string; italic: boolean; size: number; padding: string; shadow?: string; enter: 'wipe' | 'pop' | 'cut';
}> = {
	// ref_7820 Bethlem: black serif on a flat yellow label that wipes in
	label: {color: '#141210', background: '#FAEC4D', italic: false, size: 50, padding: '6px 16px 8px', enter: 'wipe'},
	// ref_308c Otis: light italic serif on a deep teal box
	box: {color: '#E9F0F3', background: '#1E475E', italic: true, size: 50, padding: '4px 14px 6px', enter: 'pop'},
	// ref_dc8b Santos: bare serif, dark on light pictures
	plain: {color: '#1D1A16', italic: false, size: 76, padding: '0', enter: 'cut'},
	// the same bare serif, light on dark pictures
	plain_light: {color: '#EDE8DD', italic: false, size: 76, padding: '0', shadow: '0 2px 18px rgba(0,0,0,0.55)', enter: 'cut'},
};

export const CAPTION_Y = 0.56; // centre of the caption line, share of frame height (the middle band)

export type Grade = 'sepia' | 'warm_print' | 'cool_mono';
export const GRADES: Record<Grade, {filter: string; tint: string; tintOpacity: number}> = {
	// Santos / Cartier: brown sepia on cream paper
	sepia: {filter: 'sepia(0.6) saturate(0.9) contrast(1.06) brightness(1.02)', tint: '#C8A97A', tintOpacity: 0.1},
	// Otis: warm, darker print with the colour still in it
	warm_print: {filter: 'sepia(0.3) saturate(1.05) contrast(1.12) brightness(0.94)', tint: '#7A4A1E', tintOpacity: 0.12},
	// Bethlem: grey engraving, almost monochrome
	cool_mono: {filter: 'grayscale(0.9) contrast(1.1) brightness(1.03)', tint: '#9FA6A8', tintOpacity: 0.08},
};
