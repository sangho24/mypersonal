"""SLIDES.md → editable .pptx via python-pptx.

marp 가 만든 pptx 는 슬라이드를 통째로 이미지로 굽기 때문에 (a) 텍스트 잘림,
(b) PowerPoint 에서 편집 불가. 이 스크립트는 SLIDES.md 의 marp 마크다운을 파싱해서
title / bullet / image / footer / speaker note 를 *개별 객체* 로 만드는 진짜 pptx.

각 슬라이드 구조:
  - Title shape (상단, 28pt bold)
  - Image shape (있으면 우측, height-fit)
  - Body text shape (좌측 또는 전체 폭, 자동 폰트 크기)
  - Footer shape (있으면 하단, 10pt italic)
  - Speaker notes (notes slide)

Usage:
    PYTHONPATH=. uv run python scripts/personal/build_deck_pptx.py
"""
from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
SLIDES_MD = ROOT / "docs" / "personal" / "SLIDES.md"
OUT_PPTX = Path("/Users/sangho/Downloads/digital_twin_deck_rev5_python.pptx")

# ─── 컬러 & 폰트 ───
COLOR_TITLE = RGBColor(0x1A, 0x1A, 0x1A)
COLOR_TEXT = RGBColor(0x33, 0x33, 0x33)
COLOR_BOLD = RGBColor(0x10, 0x10, 0x10)
COLOR_FOOTER = RGBColor(0x77, 0x77, 0x77)
COLOR_ACCENT = RGBColor(0x3A, 0x6E, 0xA5)
COLOR_QUOTE = RGBColor(0x55, 0x55, 0x55)

FONT_KR = "Apple SD Gothic Neo"
FONT_KR_FALLBACK = "맑은 고딕"  # Windows fallback (pptx uses primary on Mac/Win)

# 슬라이드 크기 (16:9)
SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5

# ─── Markdown 파싱 ───
NOTE_RE = re.compile(r"<!--\s*발표노트:\s*(.+?)\s*-->", re.DOTALL)
BG_IMG_RE = re.compile(r"!\[bg right:(\d+)%\s+fit\]\(([^)]+)\)")
FOOTER_LINE_RE = re.compile(r"^>\s*<small>(.+?)</small>\s*$")
INLINE_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def parse_slides(md_text: str) -> list[dict]:
    lines = md_text.splitlines()
    # marp frontmatter 스킵
    if lines and lines[0].strip() == "---":
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
            lines = lines[end + 1:]
        except StopIteration:
            pass

    slides: list[dict] = []
    cur: list[str] = []
    for line in lines:
        if line.strip() == "---":
            if any(s.strip() for s in cur):
                slides.append(_parse_slide("\n".join(cur)))
            cur = []
        else:
            cur.append(line)
    if any(s.strip() for s in cur):
        slides.append(_parse_slide("\n".join(cur)))
    return slides


def _parse_slide(block: str) -> dict:
    out = {"title": "", "body": [], "image_path": None, "image_pct": 35, "footer": None, "note": None}

    # speaker note 추출
    m = NOTE_RE.search(block)
    if m:
        note = m.group(1).strip()
        # estimated_seconds 분리
        note = re.sub(r"\s*\|\s*estimated_seconds:.*$", "", note, flags=re.MULTILINE)
        out["note"] = note
        block = NOTE_RE.sub("", block)

    # bg image 추출
    m = BG_IMG_RE.search(block)
    if m:
        out["image_pct"] = int(m.group(1))
        rel = m.group(2)
        path = (SLIDES_MD.parent / rel).resolve()
        out["image_path"] = path if path.exists() else None
        block = BG_IMG_RE.sub("", block)

    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            out["title"] = line[2:].strip()
            continue
        m_f = FOOTER_LINE_RE.match(line.strip())
        if m_f:
            out["footer"] = m_f.group(1).strip()
            continue
        out["body"].append(line)
    return out


def _strip_inline(text: str) -> str:
    """Render to plain text — strip ** ** but keep words. Used as fallback."""
    text = INLINE_LINK_RE.sub(r"\1", text)
    text = INLINE_BOLD_RE.sub(r"\1", text)
    text = INLINE_CODE_RE.sub(r"\1", text)
    return text


def _split_runs(text: str) -> list[tuple[str, bool, bool]]:
    """텍스트를 (segment, bold, monospace) 튜플로 분할.

    **xxx** → bold, `xxx` → monospace, 나머지는 normal.
    """
    text = INLINE_LINK_RE.sub(r"\1", text)
    runs: list[tuple[str, bool, bool]] = []
    i = 0
    cur = ""
    while i < len(text):
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end >= 0:
                if cur:
                    runs.append((cur, False, False))
                    cur = ""
                runs.append((text[i + 2:end], True, False))
                i = end + 2
                continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end >= 0:
                if cur:
                    runs.append((cur, False, False))
                    cur = ""
                runs.append((text[i + 1:end], False, True))
                i = end + 1
                continue
        cur += text[i]
        i += 1
    if cur:
        runs.append((cur, False, False))
    return runs


def _set_korean_font(run, size_pt: float, *, bold: bool = False, italic: bool = False,
                     color: RGBColor = COLOR_TEXT, mono: bool = False) -> None:
    f = run.font
    f.name = "Menlo" if mono else FONT_KR
    f.size = Pt(size_pt)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color


def _add_body_paragraph(tf, line: str, base_size: float) -> None:
    """body 한 줄을 paragraph 로 추가. bullet level, bold/mono inline 분리."""
    # blockquote
    is_quote = line.lstrip().startswith("> ")
    if is_quote:
        line = line.lstrip()[2:]

    # bullet level
    stripped = line.lstrip()
    if stripped.startswith("- "):
        level = (len(line) - len(stripped)) // 2  # 들여쓰기 2 칸 단위
        text = stripped[2:]
        is_bullet = True
    elif stripped.startswith("* "):
        level = (len(line) - len(stripped)) // 2
        text = stripped[2:]
        is_bullet = True
    else:
        level = 0
        text = line
        is_bullet = False

    # 표 (markdown table) 행은 일단 plain text 로 (정렬 유지)
    if text.strip().startswith("|"):
        text = text.replace("|", "  |  ").strip()

    # paragraph 추가
    if tf.paragraphs[0].text == "" and len(tf.paragraphs) == 1:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.level = max(0, min(4, level))
    p.alignment = PP_ALIGN.LEFT

    # 시작 prefix (bullet 글머리)
    prefix = ""
    if is_bullet:
        prefix = "•   " if level == 0 else ("◦   " if level == 1 else "▪   ")
    elif is_quote:
        prefix = "“ "

    # bold-only 한 줄이면 헤더로
    is_header_line = text.startswith("**") and text.rstrip().endswith("**") and not is_bullet

    runs_data = _split_runs(text)

    # 첫 run 에 prefix 부착
    first = True
    for seg, bold, mono in runs_data:
        if not seg:
            continue
        if first and prefix:
            seg = prefix + seg
            first = False
        elif first:
            first = False
        r = p.add_run()
        r.text = seg
        size = base_size + (1 if is_header_line else 0)
        color = COLOR_BOLD if (bold or is_header_line) else (COLOR_QUOTE if is_quote else COLOR_TEXT)
        _set_korean_font(r, size, bold=(bold or is_header_line), italic=is_quote, color=color, mono=mono)


def build_deck() -> None:
    md = SLIDES_MD.read_text()
    slides_data = parse_slides(md)

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)

    blank = prs.slide_layouts[6]

    for idx, sd in enumerate(slides_data, start=1):
        slide = prs.slides.add_slide(blank)

        # ─── Title ───
        if sd["title"]:
            t_box = slide.shapes.add_textbox(Inches(0.45), Inches(0.30), Inches(12.4), Inches(0.95))
            t_tf = t_box.text_frame
            t_tf.word_wrap = True
            t_tf.margin_top = Emu(0)
            t_tf.margin_bottom = Emu(0)
            p = t_tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            # 제목 내 **bold** 도 처리
            for seg, bold, mono in _split_runs(sd["title"]):
                r = p.add_run()
                r.text = seg
                _set_korean_font(r, 26 if len(sd["title"]) > 32 else 28, bold=True, color=COLOR_TITLE, mono=mono)

        # ─── Image (우측) ───
        body_left = Inches(0.5)
        body_top = Inches(1.45)
        body_width = Inches(SLIDE_W_IN - 1.0)
        body_height = Inches(5.5)

        if sd["image_path"]:
            pct = max(28, min(58, sd["image_pct"])) / 100.0
            img_area_w = SLIDE_W_IN * pct
            img_area_h = SLIDE_H_IN - 1.7  # title 아래부터 footer 위까지
            img_left = Inches(SLIDE_W_IN - img_area_w - 0.35)
            img_top = Inches(1.45)
            # 비율 유지를 위해 height 만 지정
            slide.shapes.add_picture(str(sd["image_path"]), img_left, img_top, height=Inches(img_area_h))
            # body 폭 축소
            body_width = Inches(SLIDE_W_IN - img_area_w - 1.1)

        # ─── Body ───
        if sd["body"]:
            # 텍스트 밀도에 따라 폰트 크기 결정
            total_chars = sum(len(line) for line in sd["body"])
            n_lines = len(sd["body"])
            if total_chars > 800 or n_lines > 12:
                base_size = 11
            elif total_chars > 500 or n_lines > 8:
                base_size = 12.5
            else:
                base_size = 14

            b_box = slide.shapes.add_textbox(body_left, body_top, body_width, body_height)
            b_tf = b_box.text_frame
            b_tf.word_wrap = True
            b_tf.margin_top = Emu(0)
            b_tf.margin_bottom = Emu(0)
            b_tf.margin_left = Emu(0)
            b_tf.margin_right = Emu(0)
            for line in sd["body"]:
                _add_body_paragraph(b_tf, line, base_size)

        # ─── Footer ───
        if sd["footer"]:
            f_box = slide.shapes.add_textbox(Inches(0.45), Inches(SLIDE_H_IN - 0.55), Inches(SLIDE_W_IN - 1.5), Inches(0.45))
            f_tf = f_box.text_frame
            f_tf.word_wrap = True
            f_tf.margin_top = Emu(0)
            f_tf.margin_bottom = Emu(0)
            text = re.sub(r"<[^>]+>", "", sd["footer"])
            text = _strip_inline(text)
            p = f_tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = text
            _set_korean_font(r, 9.5, italic=True, color=COLOR_FOOTER)

        # ─── Speaker notes ───
        if sd["note"]:
            notes = slide.notes_slide.notes_text_frame
            notes.text = sd["note"]
            for p in notes.paragraphs:
                for r in p.runs:
                    r.font.name = FONT_KR
                    r.font.size = Pt(10)

        # ─── slide number 작게 우측 하단 ───
        n_box = slide.shapes.add_textbox(Inches(SLIDE_W_IN - 0.6), Inches(SLIDE_H_IN - 0.45), Inches(0.5), Inches(0.3))
        n_tf = n_box.text_frame
        n_tf.margin_top = Emu(0); n_tf.margin_bottom = Emu(0)
        p = n_tf.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        r = p.add_run()
        r.text = str(idx)
        _set_korean_font(r, 10, color=COLOR_FOOTER)

    OUT_PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PPTX)
    print(f"saved → {OUT_PPTX} ({len(slides_data)} slides)")


if __name__ == "__main__":
    build_deck()
