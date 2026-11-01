#!/usr/bin/env bash
# Generate the synthetic fixtures described in fixtures/README.md. Requires ffmpeg >= 6.
set -euo pipefail
OUT="$(cd "$(dirname "$0")/.." && pwd)/fixtures/synthetic"
mkdir -p "$OUT"
cd "$OUT"
has_filter() { ffmpeg -hide_banner -filters 2>/dev/null | grep -qE " $1 "; }

# 1. CFR 30 fps, 6 s, three 2-second colour blocks (hard cuts at 2 s and 4 s)
ffmpeg -y -loglevel error \
  -f lavfi -i "color=c=0xF4EDDF:s=1080x1920:r=30:d=2" \
  -f lavfi -i "color=c=0x2B2B2B:s=1080x1920:r=30:d=2" \
  -f lavfi -i "color=c=0x9E7852:s=1080x1920:r=30:d=2" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=6" \
  -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]" -map "[v]" -map 3:a \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -shortest -movflags +faststart cfr_30.mp4

# 2. VFR: 24 + 30 + 60 fps segments concatenated without resampling
for r in 24 30 60; do
  ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=540x960:r=$r:d=2" -c:v libx264 -pix_fmt yuv420p -crf 20 seg_$r.mp4
done
printf "file 'seg_24.mp4'\nfile 'seg_30.mp4'\nfile 'seg_60.mp4'\n" > concat.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i concat.txt -c copy vfr_mixed.mp4
rm -f seg_24.mp4 seg_30.mp4 seg_60.mp4 concat.txt

# 3. One white frame at exactly 3.0 s (frame 90 of 180)
ffmpeg -y -loglevel error -f lavfi -i "color=c=0x2B2B2B:s=1080x1920:r=30:d=6" \
  -vf "geq=lum='if(eq(N,90),255,lum(X,Y))':cb='if(eq(N,90),128,cb(X,Y))':cr='if(eq(N,90),128,cr(X,Y))'" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 flash_1frame.mp4

# 4. Duplicated frames: 30 fps source resampled to 36 fps, so every 5th frame is held once (144 frames)
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=540x960:r=30:d=4" \
  -vf "fps=36" -c:v libx264 -pix_fmt yuv420p -crf 20 duplicate_frames.mp4

# 5. Rotation metadata
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=1920x1080:r=30:d=3" -c:v libx264 -pix_fmt yuv420p -crf 20 rot_src.mp4
# Write rotation both ways: display-matrix side data (ffmpeg >= 6 input option) and the legacy rotate tag.
ffmpeg -y -loglevel error -display_rotation 90 -i rot_src.mp4 -c copy -metadata:s:v:0 rotate=90 rotation_meta.mp4 && rm -f rot_src.mp4
if ! ffprobe -v error -select_streams v:0 -show_entries stream_side_data=rotation:stream_tags=rotate -of csv=p=0 rotation_meta.mp4 | grep -qE "[0-9]"; then
  echo "warning: this ffmpeg did not write rotation metadata; rotation fixture will be skipped by tests" >&2
fi

# 6. Silent (no audio stream)
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=540x960:r=30:d=3" -an -c:v libx264 -pix_fmt yuv420p -crf 20 silent.mp4

# 7. Truncated: cut the CFR file (faststart, so the moov atom survives and frames decode until the cut)
head -c $(( $(stat -f%z cfr_30.mp4 2>/dev/null || stat -c%s cfr_30.mp4) / 2 )) cfr_30.mp4 > truncated.mp4

# 8. Caption visible for exactly one frame (frame 60)
if has_filter drawtext; then
  ffmpeg -y -loglevel error -f lavfi -i "color=c=0xF4EDDF:s=1080x1920:r=30:d=4" \
    -vf "drawtext=text='ONE FRAME':fontsize=96:fontcolor=0x2B2B2B:x=(w-text_w)/2:y=1200:enable='eq(n,60)'" \
    -c:v libx264 -pix_fmt yuv420p -crf 18 caption_1frame.mp4
else
  python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
font = None
for path in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial.ttf"):
    try:
        font = ImageFont.truetype(path, 96)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()
d.rectangle((90, 1140, 990, 1300), fill=(255, 255, 255, 255))
d.text((140, 1165), "ONE FRAME", fill=(20, 20, 20, 255), font=font)
img.save("caption_overlay.png")
PY
  ffmpeg -y -loglevel error -f lavfi -i "color=c=0xF4EDDF:s=1080x1920:r=30:d=4" -i caption_overlay.png \
    -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,60)'" -c:v libx264 -pix_fmt yuv420p -crf 18 caption_1frame.mp4
  echo "note: drawtext not available in this ffmpeg; caption fixture used a PNG overlay" >&2
fi

# 9-10. Motion fixtures use a static, non-periodic textured image so the only motion is the camera's.
python3 - <<'PY'
import numpy as np
from PIL import Image, ImageDraw
rng = np.random.RandomState(7)
w, h = 1600, 960
base = rng.rand(h // 8, w // 8)
img = np.kron(base, np.ones((8, 8)))                      # blocky low-frequency texture
noise = rng.rand(h, w) * 0.15
arr = np.clip(0.25 + 0.5 * img + noise, 0, 1)
rgb = np.stack([arr * 244 / 255, arr * 237 / 255, arr * 223 / 255], axis=-1)
im = Image.fromarray((rgb * 255).astype("uint8"))
d = ImageDraw.Draw(im)
for _ in range(60):                                        # a few hard-edged shapes for strong features
    x, y = rng.randint(0, w - 120), rng.randint(0, h - 120)
    r = rng.randint(20, 110)
    col = tuple(int(c) for c in rng.randint(20, 235, 3))
    (d.ellipse if rng.rand() < 0.5 else d.rectangle)((x, y, x + r, y + r), fill=col)
im.save("texture_1600x960.png")
PY
# 9. Camera pan to the right: a 540x960 window slides left-to-right over the texture (content moves left on screen)
ffmpeg -y -loglevel error -loop 1 -framerate 30 -t 4 -i texture_1600x960.png \
  -vf "crop=540:960:x='(iw-540)*t/4':y=0" -c:v libx264 -pix_fmt yuv420p -crf 18 pan_right.mp4

# 10. Apparent push-in: continuous zoom into the centre of the texture (positive flow divergence)
ffmpeg -y -loglevel error -loop 1 -framerate 30 -t 4 -i texture_1600x960.png \
  -vf "crop=540:960:x=540:y=0,zoompan=z='1+0.25*on/120':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=540x960:fps=30" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 push_in.mp4
rm -f texture_1600x960.png

echo "fixtures written to $OUT"
ls -la "$OUT"
