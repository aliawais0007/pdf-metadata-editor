#!/usr/bin/env python3
"""
Generate PNG and ICNS icons from the SVG source.

Requires: cairosvg, pillow, iconutil (macOS built-in)

Usage: python scripts/generate_icons.py
"""
import os
from pathlib import Path
from PIL import Image
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "assets" / "icon.svg"
OUT = ROOT / "assets"

SIZES = [16, 32, 64, 128, 256, 512, 1024]


def main():
    OUT.mkdir(exist_ok=True)
    if not SVG.exists():
        print("No SVG icon found at", SVG)
        return
    # generate PNGs
    for s in SIZES:
        out_path = OUT / f"icon_{s}x{s}.png"
        cairosvg.svg2png(url=str(SVG), write_to=str(out_path), output_width=s, output_height=s)
        print("Wrote", out_path)

    # create a 512x512 main png
    main_png = OUT / "icon.png"
    cairosvg.svg2png(url=str(SVG), write_to=str(main_png), output_width=512, output_height=512)
    print("Wrote", main_png)

    # create .iconset folder for iconutil
    iconset = OUT / "icon.iconset"
    if iconset.exists():
        for f in iconset.iterdir():
            f.unlink()
    else:
        iconset.mkdir()

    for s in [16,32,64,128,256,512]:
        png = OUT / f"icon_{s}x{s}.png"
        if png.exists():
            # iconutil expects specific names
            name = f"icon_{s}x{s}.png"
            (iconset / name).write_bytes(png.read_bytes())

    # build icns using iconutil (macOS only)
    icns = OUT / "icon.icns"
    if (Path('/usr/bin/iconutil')).exists():
        os.system(f"/usr/bin/iconutil -c icns {iconset} -o {icns}")
        print("Wrote", icns)
    else:
        print("iconutil not found; please run iconutil manually to create .icns from icon.iconset")


if __name__ == '__main__':
    main()
