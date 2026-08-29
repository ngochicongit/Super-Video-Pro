from __future__ import annotations

import math
import re

from .alignment_models import SubtitleLayout, SubtitleReport, WordTiming, WordsDocument
from .errors import AlignmentError


def format_ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def split_caption_words(words: list[WordTiming], *, max_words: int = 7) -> list[list[WordTiming]]:
    groups: list[list[WordTiming]] = []
    current: list[WordTiming] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words or word.word.rstrip().endswith((".", ",", "!", "?", ";", ":")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _line_break(group: list[WordTiming], max_words: int, max_lines: int) -> list[list[WordTiming]]:
    if len(group) <= max_words:
        return [group]
    lines = math.ceil(len(group) / max_words)
    if lines > max_lines:
        raise AlignmentError("Caption exceeds configured line count")
    pivot = math.ceil(len(group) / lines)
    return [group[index:index + pivot] for index in range(0, len(group), pivot)]


def _estimate_width(text: str, font_size: int) -> float:
    # Conservative libass-independent estimate; Vietnamese diacritics do not change glyph advance.
    wide = sum(1 for char in text if char.upper() in "MWƯƠ")
    return len(text) * font_size * 0.56 + wide * font_size * 0.12


def choose_font_size(groups: list[list[WordTiming]], layout: SubtitleLayout) -> int:
    available = layout.width - 2 * layout.horizontal_margin_px
    for size in range(layout.preferred_font_size, layout.minimum_font_size - 1, -2):
        fits = True
        for group in groups:
            for line in _line_break(group, layout.max_words_per_line, layout.max_lines):
                if _estimate_width(" ".join(word.word for word in line), size) > available:
                    fits = False
                    break
            if not fits:
                break
        if fits:
            line_height = int(size * 1.25)
            subtitle_top = layout.height - layout.bottom_safe_px - layout.max_lines * line_height
            if subtitle_top >= layout.top_safe_px:
                return size
    raise AlignmentError("Subtitle overflow: text cannot fit inside configured safe area")


def generate_ass(document: WordsDocument, layout: SubtitleLayout) -> tuple[str, SubtitleReport]:
    all_groups: list[tuple[list[WordTiming], float]] = []
    for scene in document.scenes:
        all_groups.extend((group, scene.offset_seconds)
                          for group in split_caption_words(scene.words,
                                                           max_words=layout.max_words_per_line))
    groups = [item[0] for item in all_groups]
    font_size = choose_font_size(groups, layout) if groups else layout.preferred_font_size
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {layout.width}
PlayResY: {layout.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: NewsVi,{layout.font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{layout.outline_px},2,2,{layout.horizontal_margin_px},{layout.horizontal_margin_px},{layout.bottom_safe_px},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue: list[str] = []
    for group, offset in all_groups:
        start = group[0].start + offset
        end = group[-1].end + offset
        lines = _line_break(group, layout.max_words_per_line, layout.max_lines)
        parts: list[str] = []
        for line_index, line in enumerate(lines):
            for word in line:
                duration_cs = max(1, int(round((word.end - word.start) * 100)))
                parts.append(f"{{\\k{duration_cs}}}{escape_ass(word.word)}")
            if line_index < len(lines) - 1:
                parts.append(r"\N")
        text = " ".join(parts).replace(r" \N ", r"\N")
        dialogue.append(
            f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},NewsVi,,0,0,0,,{{\\an2}}{text}"
        )
    content = header + "\n".join(dialogue) + ("\n" if dialogue else "")
    # Reject unescaped ASS override injection from aligned text.
    if re.search(r"(?<!\\)\{(?!\\(?:an2|k\d+))", "\n".join(dialogue)):
        raise AlignmentError("Unsafe ASS override sequence detected")
    report = SubtitleReport(dialogue_count=len(dialogue), font_size=font_size,
                            top_safe_px=layout.top_safe_px, bottom_safe_px=layout.bottom_safe_px,
                            max_words_per_line=layout.max_words_per_line)
    return content, report
