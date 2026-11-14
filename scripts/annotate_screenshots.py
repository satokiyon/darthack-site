#!/usr/bin/env python3
"""
DartHack マニュアル用スクリーンショット注釈（番号付き枠線・丸数字バッジ）生成スクリプト。

annotations/<lang>.json の定義に基づき、raw_screenshots/<lang>/*.png に
番号付きの枠線と丸バッジを焼き込んで images/manual/<lang>/*.png へ出力する。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# 視認性と白文字コントラストを両立した8色パレット（style.css の .badge-num-* と同期）
COLOR_PALETTE: list[tuple[int, int, int]] = [
    (229, 57, 53),    # 1: Vivid Red     (#E53935)
    (30, 136, 229),   # 2: Vivid Blue    (#1E88E5)
    (22, 163, 74),    # 3: Vivid Green   (#16A34A)
    (234, 88, 12),    # 4: Vivid Orange  (#EA580C)
    (147, 51, 234),   # 5: Vivid Purple  (#9333EA)
    (8, 145, 178),    # 6: Vivid Teal    (#0891B2)
    (219, 39, 119),   # 7: Vivid Pink    (#DB2777)
    (202, 138, 4),    # 8: Rich Gold     (#CA8A04)
]

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """利用可能な太字フォントを読み込む。"""
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def parse_color(ann: dict[str, Any], idx: int) -> tuple[int, int, int]:
    """注釈定義から RGB カラーを取得する。"""
    if "color" in ann and isinstance(ann["color"], str):
        hex_str = ann["color"].lstrip("#")
        if len(hex_str) == 6:
            return (
                int(hex_str[0:2], 16),
                int(hex_str[2:4], 16),
                int(hex_str[4:6], 16),
            )
    color_index = (int(ann.get("id", idx + 1)) - 1) % len(COLOR_PALETTE)
    return COLOR_PALETTE[color_index]


def to_pixel_box(
    box: list[float], width: int, height: int
) -> tuple[int, int, int, int]:
    """正規化座標 (0.0〜1.0) またはピクセル座標をピクセル矩形へ変換する。"""
    if len(box) != 4:
        raise ValueError(f"box must have 4 numbers, got: {box}")
    x1, y1, x2, y2 = box
    is_normalized = all(0.0 <= v <= 1.0 for v in box)
    if is_normalized:
        px1 = round(x1 * width)
        py1 = round(y1 * height)
        px2 = round(x2 * width)
        py2 = round(y2 * height)
    else:
        px1, py1, px2, py2 = round(x1), round(y1), round(x2), round(y2)
    px1 = max(0, min(width - 1, px1))
    py1 = max(0, min(height - 1, py1))
    px2 = max(px1 + 1, min(width - 1, px2))
    py2 = max(py1 + 1, min(height - 1, py2))
    return (px1, py1, px2, py2)


def compute_badge_center(
    rect: tuple[int, int, int, int],
    badge_pos: str,
    radius: int,
    width: int,
    height: int,
    custom_xy: list[float] | None = None,
) -> tuple[int, int]:
    """枠線位置と badge_pos から丸バッジの中心座標を算出し画像内にクランプする。"""
    x1, y1, x2, y2 = rect
    if custom_xy and len(custom_xy) == 2:
        cx_raw, cy_raw = custom_xy
        if 0.0 <= cx_raw <= 1.0 and 0.0 <= cy_raw <= 1.0:
            cx, cy = round(cx_raw * width), round(cy_raw * height)
        else:
            cx, cy = round(cx_raw), round(cy_raw)
    else:
        offset = round(radius * 0.65)
        mapping = {
            "top-left": (x1 + offset, y1 + offset),
            "top-right": (x2 - offset, y1 + offset),
            "bottom-left": (x1 + offset, y2 - offset),
            "bottom-right": (x2 - offset, y2 - offset),
            "outside-top-left": (x1 - offset, y1 - offset),
            "outside-top-right": (x2 + offset, y1 - offset),
            "outside-bottom-left": (x1 - offset, y2 + offset),
            "outside-bottom-right": (x2 + offset, y2 + offset),
            "center-top": ((x1 + x2) // 2, y1),
            "center-bottom": ((x1 + x2) // 2, y2),
            "center-left": (x1, (y1 + y2) // 2),
            "center-right": (x2, (y1 + y2) // 2),
            "corner-top-left": (x1, y1),
            "corner-top-right": (x2, y1),
            "corner-bottom-left": (x1, y2),
            "corner-bottom-right": (x2, y2),
        }
        cx, cy = mapping.get(badge_pos, (x1, y1))

    margin = radius + 4
    cx = max(margin, min(width - margin, cx))
    cy = max(margin, min(height - margin, cy))
    return (cx, cy)


def annotate_image(
    src_path: Path, dst_path: Path, spec: dict[str, Any]
) -> None:
    """1枚の画像に番号付き枠線と丸数字バッジを描画して保存する。"""
    base = Image.open(src_path).convert("RGBA")
    width, height = base.size
    short_side = min(width, height)

    # 画面解像度に合わせた線幅・角丸・バッジサイズを決定
    stroke_w = max(4, round(short_side * 0.0055))
    corner_r = max(8, round(short_side * 0.012))
    badge_r = max(20, round(short_side * 0.026))
    font_size = round(badge_r * 1.15)
    font = load_bold_font(font_size)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    annotations = spec.get("annotations", [])

    # 1パス目: 枠線をすべて描画（バッジが枠線に隠れないよう分離）
    parsed_items: list[tuple[tuple[int, int, int, int], tuple[int, int, int], dict[str, Any]]] = []
    for idx, ann in enumerate(annotations):
        rect = to_pixel_box(ann["box"], width, height)
        color = parse_color(ann, idx)
        parsed_items.append((rect, color, ann))

        # わずかに薄い背景ティントを入れて対象領域を視認しやすくする
        draw.rounded_rectangle(
            rect,
            radius=corner_r,
            fill=(color[0], color[1], color[2], 22),
        )
        # 外側の白＋黒の縁取りで明暗どちらの画面でもくっきり表示
        draw.rounded_rectangle(
            rect,
            radius=corner_r,
            outline=(0, 0, 0, 210),
            width=stroke_w + 4,
        )
        draw.rounded_rectangle(
            rect,
            radius=corner_r,
            outline=(255, 255, 255, 235),
            width=stroke_w + 2,
        )
        draw.rounded_rectangle(
            rect,
            radius=corner_r,
            outline=(color[0], color[1], color[2], 255),
            width=stroke_w,
        )

    # 2パス目: 丸数字バッジを最前面に描画
    for rect, color, ann in parsed_items:
        badge_pos = ann.get("badge_pos", "corner-top-left")
        custom_xy = ann.get("badge_xy")
        cx, cy = compute_badge_center(
            rect, badge_pos, badge_r, width, height, custom_xy
        )
        label = str(ann["id"])

        # ドロップシャドウ
        shadow_offset = max(2, round(badge_r * 0.12))
        draw.ellipse(
            [
                cx - badge_r + shadow_offset,
                cy - badge_r + shadow_offset,
                cx + badge_r + shadow_offset,
                cy + badge_r + shadow_offset,
            ],
            fill=(0, 0, 0, 140),
        )
        # 白外枠 + カラー円
        ring_w = max(3, round(badge_r * 0.14))
        draw.ellipse(
            [cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r],
            fill=(color[0], color[1], color[2], 255),
            outline=(255, 255, 255, 255),
            width=ring_w,
        )

        # 数字の視覚的中央配置
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
        draw.text((tx, ty), label, font=font, fill=(255, 255, 255, 255))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(dst_path, format="PNG", optimize=True)


def validate_annotations(
    data: dict[str, Any], raw_dir: Path
) -> list[str]:
    """注釈定義 JSON の妥当性と対象画像の存在を検証する。"""
    errors: list[str] = []
    for filename, spec in data.items():
        src_path = raw_dir / filename
        if not src_path.exists():
            errors.append(f"Missing raw image: {src_path}")
        annotations = spec.get("annotations", [])
        seen_ids: set[int] = set()
        for ann in annotations:
            ann_id = ann.get("id")
            if not isinstance(ann_id, int) or ann_id <= 0:
                errors.append(f"{filename}: invalid id {ann_id!r}")
            elif ann_id in seen_ids:
                errors.append(f"{filename}: duplicate id {ann_id}")
            else:
                seen_ids.add(ann_id)
            box = ann.get("box")
            if not isinstance(box, list) or len(box) != 4:
                errors.append(f"{filename} id={ann_id}: invalid box {box!r}")
                continue
            x1, y1, x2, y2 = box
            if not (x1 < x2 and y1 < y2):
                errors.append(f"{filename} id={ann_id}: box x1<x2 and y1<y2 required: {box}")
            if all(isinstance(v, (int, float)) for v in box):
                if all(v <= 1.0 for v in box) and any(v < 0.0 for v in box):
                    errors.append(f"{filename} id={ann_id}: negative normalized coord: {box}")
    return errors


def process_language(repo_root: Path, lang: str, check_only: bool) -> int:
    """指定言語（ja / en）の注釈画像を生成または検証する。"""
    ann_path = repo_root / "annotations" / f"{lang}.json"
    raw_dir = repo_root / "raw_screenshots" / lang
    out_dir = repo_root / "images" / "manual" / lang

    if not ann_path.exists():
        print(f"[{lang}] Annotation file not found: {ann_path}", file=sys.stderr)
        return 1

    data = json.loads(ann_path.read_text(encoding="utf-8"))
    errors = validate_annotations(data, raw_dir)
    if errors:
        for err in errors:
            print(f"[{lang}] ERROR: {err}", file=sys.stderr)
        return 1

    if check_only:
        print(f"[{lang}] Validation OK ({len(data)} images)")
        return 0

    for filename, spec in data.items():
        src_path = raw_dir / filename
        dst_path = out_dir / filename
        annotate_image(src_path, dst_path, spec)
        print(f"[{lang}] Generated: {dst_path.relative_to(repo_root)}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate DartHack manual screenshots.")
    parser.add_argument(
        "--lang",
        choices=["ja", "en", "all"],
        default="all",
        help="Target language to process",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate JSON and source images without generating files",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    langs = ["ja", "en"] if args.lang == "all" else [args.lang]

    exit_code = 0
    for lang in langs:
        rc = process_language(repo_root, lang, args.check_only)
        if rc != 0:
            exit_code = rc
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
