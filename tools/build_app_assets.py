#!/usr/bin/env python3
"""Готовит лёгкие версии изображений для приложения из оригиналов.

Использование: python tools/build_app_assets.py --src <папка с оригиналами> --out design/assets

Оригиналы (PNG/JPG от дизайнера) в репозиторий не кладутся: слишком тяжёлые. В репозитории лежит результат работы
этого скрипта и опись `manifest.json`. Требуется Pillow с поддержкой WebP.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Что в приложение пока не берём: картинки ждут переделки (см. docs/ASSETS.md)
SKIP = {"onboarding_2.png", "google_play_1024x500.png", "social_share_1200x630.png"}


def _save_webp(im: Image.Image, path: Path, quality: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=quality, method=6)


def _fit(im: Image.Image, width: int) -> Image.Image:
    if im.width <= width:
        return im
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def detect_disc(im: Image.Image, tol: int = 5):
    """Границы круга, «запечённого» в аватар (круг чуть темнее фона)."""
    a = np.array(im.convert("RGB")).astype(int)
    h, w, _ = a.shape
    corner = a[:6, :6].reshape(-1, 3).mean(axis=0)

    def edge(line):
        d = corner[2] - line[:, 2]
        for i in range(len(d) - 3):
            if d[i] > tol and d[i + 1] > tol and d[i + 2] > tol:
                return i
        return 0

    my, mx = h // 2, w // 2
    return edge(a[my]), edge(a[:, mx]), w - 1 - edge(a[my][::-1]), h - 1 - edge(a[:, mx][::-1])


def circle_avatar(path: Path) -> Image.Image:
    """Чистый круг с прозрачными углами: белый ободок и квадратный фон убираются."""
    im = Image.open(path).convert("RGB")
    left, top, right, bottom = detect_disc(im)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    side = min(right - left, bottom - top) * 0.975
    box = tuple(round(v) for v in (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2))
    square = im.crop(box).resize((512, 512), Image.LANCZOS)
    big = Image.new("L", (2048, 2048), 0)
    ImageDraw.Draw(big).ellipse((0, 0, 2047, 2047), fill=255)
    rgba = square.convert("RGBA")
    rgba.putalpha(big.resize((512, 512), Image.LANCZOS))
    return rgba


def silhouette(logo: Image.Image, size: int = 96) -> Image.Image:
    """Белый силуэт знака для значка уведомлений Android (тёмная дверь вырезается)."""
    arr = np.array(logo.convert("RGBA")).astype(np.float32)
    alpha = np.where(arr[..., :3].mean(axis=2) < 70, 0, arr[..., 3])
    mask = Image.fromarray(alpha.astype("uint8"))
    mask = mask.crop(mask.point(lambda v: 255 if v > 8 else 0).getbbox())
    scale = (size - 12) / max(mask.size)
    mask = mask.resize((round(mask.width * scale), round(mask.height * scale)), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
    white.putalpha(mask)
    out.alpha_composite(white, ((size - mask.width) // 2, (size - mask.height) // 2))
    return out


def build(src: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    produced: list[tuple[Path, str]] = []

    for i in range(1, 9):
        face = circle_avatar(src / "avatars" / f"avatar_{i}.png")
        for size in (512, 256):
            target = out / "avatars" / f"avatar_{i}_{size}.webp"
            _save_webp(face.resize((size, size), Image.LANCZOS), target, 88)
            produced.append((target, f"аватар {i}, {size} px"))

    for path in sorted((src / "icons").glob("icon_*.png")):
        target = out / "icons" / f"{path.stem}.webp"
        _save_webp(_fit(Image.open(path).convert("RGBA"), 512), target, 90)
        produced.append((target, "иконка раздела"))

    widths = {"banner_rides.png": 1200, "onboarding_1.png": 960, "onboarding_3.png": 960}
    for path in sorted((src / "illustrations").glob("*.png")):
        if path.name in SKIP:
            continue
        target = out / "illustrations" / f"{path.stem}.webp"
        _save_webp(_fit(Image.open(path).convert("RGBA"), widths.get(path.name, 800)), target, 86)
        produced.append((target, "иллюстрация"))

    for path in sorted((src / "covers").glob("cover_*.jpg")):
        image = Image.open(path).convert("RGB")
        for width, quality in ((1600, 80), (800, 78)):
            target = out / "covers" / f"{path.stem}_{width}.webp"
            _save_webp(_fit(image, width), target, quality)
            produced.append((target, f"обложка ЖК, {width} px"))

    parking = Image.open(src / "placeholders" / "parking_placeholder.jpg").convert("RGB")
    target = out / "placeholders" / "parking_placeholder.webp"
    _save_webp(_fit(parking, 1000), target, 82)
    produced.append((target, "заглушка фото парковки"))
    building = Image.open(src / "placeholders" / "building_generic.png").convert("RGBA")
    target = out / "placeholders" / "building_generic.webp"
    _save_webp(building, target, 90)
    produced.append((target, "обложка чата дома"))

    brand = out / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    logo = Image.open(src / "brand" / "logo-mark.png").convert("RGBA")
    app_icon = Image.open(src / "brand" / "app-icon-1024.png").convert("RGB")
    adaptive = Image.open(src / "brand" / "adaptive-foreground.png").convert("RGBA")
    logo.save(brand / "logo-mark.png", optimize=True)
    app_icon.save(brand / "app-icon-1024.png", optimize=True)
    adaptive.save(brand / "adaptive-foreground.png", optimize=True)
    _save_webp(_fit(logo, 512), brand / "logo-mark_512.webp", 92)
    mark = logo.crop(logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    mark = mark.resize((600, round(mark.height * 600 / mark.width)), Image.LANCZOS)
    splash = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    splash.alpha_composite(mark, ((1024 - mark.width) // 2, (1024 - mark.height) // 2))
    splash.save(brand / "splash-icon.png", optimize=True)
    app_icon.resize((48, 48), Image.LANCZOS).save(brand / "favicon.png", optimize=True)
    app_icon.resize((512, 512), Image.LANCZOS).save(brand / "play-store-icon-512.png", optimize=True)
    silhouette(logo).save(brand / "notification-icon.png", optimize=True)
    for name, role in {
        "logo-mark.png": "знак (прозрачный фон, исходник для генерации)",
        "app-icon-1024.png": "иконка приложения iOS/Android",
        "adaptive-foreground.png": "Android adaptive icon, передний план (фон #FF5B45)",
        "logo-mark_512.webp": "знак для интерфейса",
        "splash-icon.png": "значок экрана запуска",
        "favicon.png": "значок сайта",
        "play-store-icon-512.png": "иконка для Google Play",
        "notification-icon.png": "значок уведомлений Android (белый силуэт)",
    }.items():
        produced.append((brand / name, role))

    manifest = []
    for path, role in produced:
        image = Image.open(path)
        manifest.append({
            "file": path.relative_to(out).as_posix(), "role": role, "bytes": path.stat().st_size,
            "width": image.width, "height": image.height, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest.sort(key=lambda row: row["file"])
    total = sum(row["bytes"] for row in manifest)
    (out / "manifest.json").write_text(
        json.dumps({"total_bytes": total, "files": manifest}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", default="design/assets")
    args = parser.parse_args()
    manifest, total = build(Path(args.src), Path(args.out))
    print(f"Готово: {len(manifest)} файлов, {total / 1e6:.2f} МБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
