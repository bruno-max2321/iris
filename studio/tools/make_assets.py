"""Shared assets of the template and the archival cut-out treatment.

    python3 tools/make_assets.py                      # grain tiles and paper plates into public/gen/
    python3 tools/make_assets.py cutout SRC OUT.png [--mono] [--border 18]

A cut-out is the picture printed on old paper: tone-mapped (sepia, or grey with --mono), a cream border,
transparent outside, so the template can float it over a plate and cast its shadow in CSS.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

GEN = Path(__file__).resolve().parent.parent / "public" / "gen"
W, H = 1080, 1920
rng = np.random.default_rng(11)


def grain_tiles(n: int = 6) -> None:
    for k in range(n):
        g = rng.normal(128, 38, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
        Image.fromarray(g).resize((W, H), Image.BILINEAR).save(GEN / f"grain_{k}.png", optimize=True)


def paper(name: str, rgb: tuple[int, int, int], w: int = 1500, h: int = 2660) -> None:
    """Back plate larger than the frame (camera moves need margin): flat paper with blotches and fibre noise."""
    base = np.full((h, w, 3), rgb, np.float32)
    blotch = np.array(Image.fromarray(rng.normal(0, 7, (h // 220, w // 220)).astype(np.float32)).resize((w, h), Image.BICUBIC))
    fibre = rng.normal(0, 4, (h, w)).astype(np.float32)
    base += (blotch + fibre)[..., None]
    Image.fromarray(base.clip(0, 255).astype(np.uint8)).save(GEN / f"{name}.jpg", quality=90)


def cutout(src: Path, out: Path, mono: bool = False, border: int = 18) -> None:
    im = Image.open(src).convert("RGB")
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    if mono:
        toned = ImageOps.colorize(g, black=(22, 22, 24), mid=(120, 120, 118), white=(232, 230, 224))
    else:
        toned = ImageOps.colorize(g, black=(38, 28, 18), mid=(140, 112, 78), white=(236, 222, 196))
    framed = ImageOps.expand(toned, border=border, fill=(240, 230, 208)).convert("RGBA")
    out.parent.mkdir(parents=True, exist_ok=True)
    framed.save(out)


if __name__ == "__main__":
    GEN.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "cutout":
        args = sys.argv[2:]
        b = int(args[args.index("--border") + 1]) if "--border" in args else 18
        cutout(Path(args[0]), Path(args[1]), mono="--mono" in args, border=b)
    else:
        grain_tiles()
        paper("paper_cream", (226, 212, 184))
        paper("paper_grey", (196, 196, 190))
        paper("paper_dark", (42, 34, 28))
        print(sorted(p.name for p in GEN.iterdir()))
