#!/usr/bin/env python3
"""
DartHack ユーザ向けマニュアル (Markdown -> HTML) 生成スクリプト。

正本 Markdown (manual.md / manual_en.md) をパースし、
style.css に準拠した manual.html / manual_en.html を生成する。
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

IMG_PATTERN = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
CAPTION_PATTERN = re.compile(r"^(?:\*([^*]+)\*|_([^_]+)_)\s*$")
ORDERED_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")
UNORDERED_PATTERN = re.compile(r"^[-*]\s+(.*)$")
HEADING_H2_PATTERN = re.compile(r"^##\s+(.*)$")
HEADING_H3_PATTERN = re.compile(r"^###\s+(.*)$")
SECTION_NUM_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")


@dataclass
class Section:
    number: str
    title: str
    anchor: str
    lines: list[str] = field(default_factory=list)


@dataclass
class LangConfig:
    lang: str
    md_filename: str
    html_filename: str
    page_title: str
    hero_subtitle: str
    toc_title: str
    back_home_label: str
    home_href: str
    other_lang_label: str
    other_lang_href: str
    privacy_label: str
    privacy_href: str
    footer_home_label: str
    footer_manual_label: str
    footer_privacy_label: str
    footer_other_lang_label: str
    footer_other_lang_href: str
    zoom_hint: str


LANG_CONFIGS: dict[str, LangConfig] = {
    "ja": LangConfig(
        lang="ja",
        md_filename="manual.md",
        html_filename="manual.html",
        page_title="DartHack 操作マニュアル",
        hero_subtitle="基本操作からカスタマイズ・最新機能まで網羅した公式ユーザーガイド",
        toc_title="目次",
        back_home_label="トップページへ戻る",
        home_href="index.html",
        other_lang_label="English Manual",
        other_lang_href="manual_en.html",
        privacy_label="プライバシーポリシー",
        privacy_href="privacy.html",
        footer_home_label="トップページ",
        footer_manual_label="操作マニュアル",
        footer_privacy_label="プライバシーポリシー",
        footer_other_lang_label="English",
        footer_other_lang_href="index_en.html",
        zoom_hint="画像をクリックすると拡大表示できます",
    ),
    "en": LangConfig(
        lang="en",
        md_filename="manual_en.md",
        html_filename="manual_en.html",
        page_title="DartHack User Manual",
        hero_subtitle="Complete guide covering basic controls, customization, and latest features",
        toc_title="Table of Contents",
        back_home_label="Back to Top",
        home_href="index_en.html",
        other_lang_label="日本語マニュアル",
        other_lang_href="manual.html",
        privacy_label="Privacy Policy",
        privacy_href="privacy_en.html",
        footer_home_label="Top",
        footer_manual_label="User Manual",
        footer_privacy_label="Privacy Policy",
        footer_other_lang_label="日本語",
        footer_other_lang_href="index.html?lang=ja",
        zoom_hint="Click any screenshot to zoom in",
    ),
}


def format_inline(text: str) -> str:
    """インライン Markdown（コード、太字、斜体、リンク）を HTML に変換する。"""
    code_placeholders: list[str] = []

    def replace_code(match: re.Match[str]) -> str:
        code_html = f"<code>{html.escape(match.group(1))}</code>"
        idx = len(code_placeholders)
        code_placeholders.append(code_html)
        return f"\x00CODE{idx}\x00"

    # インラインコード内の記号が太字やリンクとして誤解釈されないよう先に退避
    temp = re.sub(r"`([^`]+)`", replace_code, text)

    # リンクも一時退避（URL内のアンダースコア保護のため）
    link_placeholders: list[str] = []

    def replace_link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        extra = ""
        if url.startswith(("http://", "https://")):
            extra = ' target="_blank" rel="noopener noreferrer"'
        link_html = f'<a href="{url}"{extra}>{label}</a>'
        idx = len(link_placeholders)
        link_placeholders.append(link_html)
        return f"\x00LINK{idx}\x00"

    temp = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, temp)
    escaped = html.escape(temp)

    # 太字・斜体変換
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

    # 退避要素を復元
    for idx, link_html in enumerate(link_placeholders):
        escaped = escaped.replace(f"\x00LINK{idx}\x00", link_html)
    for idx, code_html in enumerate(code_placeholders):
        escaped = escaped.replace(f"\x00CODE{idx}\x00", code_html)

    return escaped


def parse_markdown_document(md_text: str) -> tuple[str, list[str], list[Section]]:
    """Markdown テキストをタイトル・導入部・セクション一覧に分解する。"""
    lines = md_text.splitlines()
    title = ""
    intro_lines: list[str] = []
    sections: list[Section] = []
    current_section: Section | None = None
    auto_num = 0

    for line in lines:
        if not title and line.startswith("# "):
            title = line[2:].strip()
            continue

        h2_match = HEADING_H2_PATTERN.match(line)
        if h2_match:
            raw_heading = h2_match.group(1).strip()
            num_match = SECTION_NUM_PATTERN.match(raw_heading)
            appendix_match = re.match(
                r"^(付録|Appendix)\s*([A-Za-z0-9]+)\.\s+(.*)$",
                raw_heading,
                re.I,
            )
            if num_match:
                sec_num = num_match.group(1)
                sec_title = num_match.group(2).strip()
                anchor = f"section-{sec_num}"
            elif appendix_match:
                prefix = appendix_match.group(1)
                sec_num = appendix_match.group(2).upper()
                sec_title = f"{prefix}: {appendix_match.group(3).strip()}"
                anchor = f"section-appendix-{sec_num.lower()}"
            else:
                auto_num += 1
                sec_num = str(auto_num)
                sec_title = raw_heading
                anchor = f"section-extra-{auto_num}"
            current_section = Section(number=sec_num, title=sec_title, anchor=anchor)
            sections.append(current_section)
            continue

        if current_section is None:
            # 先頭の言語切替行や目次補助コメント以外の導入文を収集
            if not line.strip().startswith("<!--"):
                intro_lines.append(line)
        else:
            current_section.lines.append(line)

    return title, intro_lines, sections


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    return all(bool(re.match(r"^:?-{3,}:?$", c)) for c in cells if c)


def split_table_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render_blocks(lines: list[str], indent: str = "      ") -> str:
    """セクション本文の Markdown 行列を HTML ブロック群に変換する。"""
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("<!--"):
            i += 1
            continue

        # 小見出し (###)
        h3_match = HEADING_H3_PATTERN.match(stripped)
        if h3_match:
            out.append(f"{indent}<h3>{format_inline(h3_match.group(1).strip())}</h3>")
            i += 1
            continue

        # 画像ブロック（連続する画像＋キャプションを .image-group にまとめる）
        if IMG_PATTERN.match(stripped):
            cards: list[tuple[str, str, str]] = []
            while i < n:
                s = lines[i].strip()
                img_match = IMG_PATTERN.match(s)
                if not img_match:
                    if not s and i + 1 < n and IMG_PATTERN.match(lines[i + 1].strip()):
                        i += 1
                        continue
                    break
                alt_text = img_match.group(1).strip()
                src_path = img_match.group(2).strip()
                caption = alt_text
                i += 1
                # 直後が *キャプション* ならそれを採用
                if i < n:
                    cap_match = CAPTION_PATTERN.match(lines[i].strip())
                    if cap_match:
                        caption = (cap_match.group(1) or cap_match.group(2) or "").strip()
                        i += 1
                cards.append((src_path, alt_text, caption))

            out.append(f'{indent}<div class="image-group">')
            for src_path, alt_text, caption in cards:
                out.append(f'{indent}  <div class="image-card">')
                out.append(
                    f'{indent}    <img src="{html.escape(src_path, quote=True)}" '
                    f'alt="{html.escape(alt_text, quote=True)}" loading="lazy">'
                )
                out.append(
                    f'{indent}    <div class="image-caption">{format_inline(caption)}</div>'
                )
                out.append(f"{indent}  </div>")
            out.append(f"{indent}</div>")
            continue

        # 引用・注記ブロック (>)
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                q_line = lines[i].strip()[1:].strip()
                if not re.match(r"^\[!(NOTE|TIP|IMPORTANT|WARNING)\]$", q_line, re.I):
                    quote_lines.append(q_line)
                i += 1
            quote_html = "<br>".join(format_inline(q) for q in quote_lines if q)
            out.append(f'{indent}<div class="manual-note">{quote_html}</div>')
            continue

        # テーブル
        if (
            stripped.startswith("|")
            and i + 1 < n
            and is_table_separator(lines[i + 1])
        ):
            headers = split_table_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_table_row(lines[i].strip()))
                i += 1
            out.append(f'{indent}<div class="table-wrap">')
            out.append(f'{indent}  <table class="manual-table">')
            out.append(f"{indent}    <thead><tr>")
            for h in headers:
                out.append(f"{indent}      <th>{format_inline(h)}</th>")
            out.append(f"{indent}    </tr></thead>")
            out.append(f"{indent}    <tbody>")
            for row in rows:
                out.append(f"{indent}      <tr>")
                for cell in row:
                    out.append(f"{indent}        <td>{format_inline(cell)}</td>")
                out.append(f"{indent}      </tr>")
            out.append(f"{indent}    </tbody>")
            out.append(f"{indent}  </table>")
            out.append(f"{indent}</div>")
            continue

        # 番号付きリスト（画像注釈番号 1..8 と色バッジ連携）
        if ORDERED_PATTERN.match(stripped):
            out.append(f'{indent}<ol class="annotated-list">')
            while i < n:
                s = lines[i].strip()
                ord_match = ORDERED_PATTERN.match(s)
                if not ord_match:
                    break
                num = int(ord_match.group(1))
                body = ord_match.group(2).strip()
                color_cls = ((num - 1) % 8) + 1
                out.append(
                    f'{indent}  <li><span class="badge-num badge-num-{color_cls}">{num}</span>'
                    f'<span class="annotated-text">{format_inline(body)}</span></li>'
                )
                i += 1
            out.append(f"{indent}</ol>")
            continue

        # 箇条書きリスト
        if UNORDERED_PATTERN.match(stripped):
            out.append(f'{indent}<ul class="manual-list">')
            while i < n:
                s = lines[i].strip()
                ul_match = UNORDERED_PATTERN.match(s)
                if not ul_match:
                    break
                out.append(f"{indent}  <li>{format_inline(ul_match.group(1).strip())}</li>")
                i += 1
            out.append(f"{indent}</ul>")
            continue

        # 通常段落
        para_lines: list[str] = []
        while i < n:
            s = lines[i].strip()
            if (
                not s
                or s.startswith("#")
                or s.startswith(">")
                or s.startswith("|")
                or IMG_PATTERN.match(s)
                or ORDERED_PATTERN.match(s)
                or UNORDERED_PATTERN.match(s)
            ):
                break
            para_lines.append(s)
            i += 1
        if para_lines:
            out.append(f'{indent}<p class="manual-desc">{" ".join(format_inline(p) for p in para_lines)}</p>')

    return "\n".join(out)


def build_html(cfg: LangConfig, md_text: str) -> str:
    """パースした Markdown から完全な HTML 文字列を組み立てる。"""
    title, intro_lines, sections = parse_markdown_document(md_text)
    page_title = title or cfg.page_title

    # 先頭導入文（最初の言語リンク行などを除いた説明段落）
    filtered_intro = [
        ln
        for ln in intro_lines
        if ln.strip() and not ln.strip().startswith(("**Language", "**言語", "---"))
    ]
    intro_html = ""
    if filtered_intro:
        intro_html = (
            '    <div class="manual-intro">\n'
            + render_blocks(filtered_intro, indent="      ")
            + "\n    </div>\n"
        )

    toc_items = "\n".join(
        f'        <li><a href="#{sec.anchor}">{html.escape(sec.number)}. {html.escape(sec.title)}</a></li>'
        for sec in sections
    )

    sections_html_parts: list[str] = []
    for sec in sections:
        body_html = render_blocks(sec.lines, indent="      ")
        sections_html_parts.append(
            f'    <!-- {html.escape(sec.number)}. {html.escape(sec.title)} -->\n'
            f'    <section id="{sec.anchor}" class="manual-item">\n'
            f'      <h2><span class="manual-item-num">{html.escape(sec.number)}</span> {html.escape(sec.title)}</h2>\n'
            f"{body_html}\n"
            f"    </section>"
        )
    sections_html = "\n\n".join(sections_html_parts)

    return f"""<!DOCTYPE html>
<html lang="{cfg.lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(page_title)}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="hero">
    <h1>{html.escape(page_title)}</h1>
    <p class="subtitle">{html.escape(cfg.hero_subtitle)}</p>
    <nav class="nav-links">
      <a href="{cfg.home_href}" class="btn btn-secondary">{html.escape(cfg.back_home_label)}</a>
      <a href="{cfg.other_lang_href}" class="btn">{html.escape(cfg.other_lang_label)}</a>
      <a href="{cfg.privacy_href}" class="btn btn-secondary">{html.escape(cfg.privacy_label)}</a>
    </nav>
  </header>

  <main class="section">
{intro_html}    <p class="zoom-tip">{html.escape(cfg.zoom_hint)}</p>

    <!-- 目次 (Table of Contents) -->
    <nav class="toc-container">
      <h2>{html.escape(cfg.toc_title)}</h2>
      <ul class="toc-list">
{toc_items}
      </ul>
    </nav>

{sections_html}
  </main>

  <!-- スクリーンショット拡大モーダル -->
  <div id="lightbox" class="lightbox" aria-hidden="true">
    <button id="lightbox-close" class="lightbox-close" aria-label="Close">&times;</button>
    <img id="lightbox-img" src="" alt="">
    <div id="lightbox-caption" class="lightbox-caption"></div>
  </div>

  <footer>
    <div class="footer-nav">
      <a href="{cfg.home_href}">{html.escape(cfg.footer_home_label)}</a> |
      <a href="{cfg.html_filename}">{html.escape(cfg.footer_manual_label)}</a> |
      <a href="{cfg.privacy_href}">{html.escape(cfg.footer_privacy_label)}</a> |
      <a href="{cfg.footer_other_lang_href}">{html.escape(cfg.footer_other_lang_label)}</a>
    </div>
    <p>© 2026 DartHack Project</p>
  </footer>

  <script>
    (function () {{
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      const lbCap = document.getElementById('lightbox-caption');
      const closeBtn = document.getElementById('lightbox-close');

      function closeLightbox() {{
        lb.classList.remove('open');
        lb.setAttribute('aria-hidden', 'true');
        lbImg.src = '';
      }}

      document.querySelectorAll('.image-card img').forEach(function (img) {{
        img.addEventListener('click', function () {{
          lbImg.src = img.src;
          lbImg.alt = img.alt;
          const cap = img.parentElement.querySelector('.image-caption');
          lbCap.textContent = cap ? cap.textContent : img.alt;
          lb.classList.add('open');
          lb.setAttribute('aria-hidden', 'false');
        }});
      }});

      lb.addEventListener('click', function (e) {{
        if (e.target === lb || e.target === closeBtn) {{
          closeLightbox();
        }}
      }});

      document.addEventListener('keydown', function (e) {{
        if (e.key === 'Escape' && lb.classList.contains('open')) {{
          closeLightbox();
        }}
      }});
    }})();
  </script>
</body>
</html>
"""


def verify_links_and_images(repo_root: Path) -> list[str]:
    """Markdown と生成 HTML 内のローカル画像・ページリンクを検証する。"""
    errors: list[str] = []
    targets = [
        "manual.md",
        "manual_en.md",
        "manual.html",
        "manual_en.html",
        "index.html",
        "index_en.html",
        "privacy.html",
        "privacy_en.html",
    ]
    for rel in targets:
        path = repo_root / rel
        if not path.exists():
            errors.append(f"Missing target file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if rel.endswith(".md"):
            refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)|\[[^\]]+\]\(([^)]+)\)", text)
            urls = [a or b for a, b in refs]
        else:
            urls = re.findall(r'(?:src|href)="([^"]+)"', text)
        for url in urls:
            if url.startswith(("http://", "https://", "#", "mailto:")):
                continue
            clean = url.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            target = (path.parent / clean).resolve()
            if not target.exists():
                errors.append(f"{rel}: broken local reference '{url}'")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HTML manuals from Markdown.")
    parser.add_argument(
        "--lang",
        choices=["ja", "en", "all"],
        default="all",
        help="Language to generate",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify links and image paths after generation",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    langs = ["ja", "en"] if args.lang == "all" else [args.lang]

    for lang in langs:
        cfg = LANG_CONFIGS[lang]
        md_path = repo_root / cfg.md_filename
        html_path = repo_root / cfg.html_filename
        if not md_path.exists():
            print(f"[{lang}] Markdown source not found: {md_path}", file=sys.stderr)
            return 1
        md_text = md_path.read_text(encoding="utf-8")
        rendered_html = build_html(cfg, md_text)
        html_path.write_text(rendered_html, encoding="utf-8")
        print(f"[{lang}] Generated: {html_path.name} from {md_path.name}")

    if args.check:
        errors = verify_links_and_images(repo_root)
        if errors:
            for err in errors:
                print(f"CHECK ERROR: {err}", file=sys.stderr)
            return 1
        print("Link & image verification passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
