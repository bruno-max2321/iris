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
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -shortest cfr_30.mp4

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
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=1920x1080:r=30:d=3" -c:v libx264 -pix_fmt yuv420p -crf 20 \
  -metadata:s:v:0 rotate=90 rotation_meta.mp4

# 6. Silent (no audio stream)
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=s=540x960:r=30:d=3" -an -c:v libx264 -pix_fmt yuv420p -crf 20 silent.mp4

# 7. Truncated: cut the CFR file in the middle of the byte stream
head -c $(( $(stat -f%z cfr_30.mp4 2>/dev/null || stat -c%s cfr_30.mp4) / 2 )) cfr_30.mp4 > truncated.mp4

# 8. Caption visible for exactly one frame (frame 60)
if has_filter drawtext; then
  ffmpeg -y -loglevel error -f lavfi -i "color=c=0xF4EDDF:s=1080x1920:r=30:d=4" \
    -vf "drawtext=text='ONE FRAME':fontsize=96:fontcolor=0x2B2B2B:x=(w-text_w)/2:y=1200:enable='eq(n,60)'" \
    -c:v libx264 -pix_fmt yuv420p -crf 18 caption_1frame.mp4
else
  python3 - <<'PY'
from PIL import Image, ImageDraw
img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle((140, 1150, 940, 1290), fill=(244, 237, 223, 255))
d.text((200, 1180), "ONE FRAME", fill=(43, 43, 43, 255))
img.save("caption_overlay.png")
PY
  ffmpeg -y -loglevel error -f lavfi -i "color=c=0xF4EDDF:s=1080x1920:r=30:d=4" -i caption_overlay.png \
    -filter_complex "[0:v][1:v]overlay=0:0:enable='eq(n,60)'" -c:v libx264 -pix_fmt yuv420p -crf 18 caption_1frame.mp4
  echo "note: drawtext not available in this ffmpeg; caption fixture used a PNG overlay" >&2
fi

echo "fixtures written to $OUT"
ls -la "$OUT"
