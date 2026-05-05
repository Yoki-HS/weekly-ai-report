import os
import logging
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

CATEGORY_ORDER = [
    "New Services & Products",
    "Research & Technology",
    "Business & Industry",
    "Other Notable Topics",
]

CATEGORY_LABELS = {
    "New Services & Products": "[NEW]  New Services & Products",
    "Research & Technology":   "[LAB]  Research & Technology",
    "Business & Industry":     "[BIZ]  Business & Industry",
    "Other Notable Topics":    "[INFO] Other Notable Topics",
}

CATEGORY_COLORS = {
    "New Services & Products": HexColor("#1a73e8"),
    "Research & Technology":   HexColor("#0f9d58"),
    "Business & Industry":     HexColor("#f29900"),
    "Other Notable Topics":    HexColor("#d93025"),
}


def _ttc_subfont_index(path: str) -> int:
    idx_file = path + ".ttc_idx"
    if os.path.exists(idx_file):
        try:
            return int(open(idx_file).read().strip())
        except Exception:
            pass
    return 0


def _register_fonts() -> tuple[str, str]:
    regular = os.path.join(FONTS_DIR, "NotoSansJP-Regular.ttf")
    bold = os.path.join(FONTS_DIR, "NotoSansJP-Bold.ttf")

    font_name = "Helvetica"
    bold_name = "Helvetica-Bold"

    if os.path.exists(regular):
        try:
            idx = _ttc_subfont_index(regular)
            pdfmetrics.registerFont(TTFont("NotoSansJP", regular, subfontIndex=idx))
            font_name = "NotoSansJP"
            logger.info(f"Regular フォント登録成功 (subfontIndex={idx})")
        except Exception as e:
            logger.warning(f"Regular フォント登録失敗: {e}")

    if os.path.exists(bold):
        try:
            idx = _ttc_subfont_index(bold)
            pdfmetrics.registerFont(TTFont("NotoSansJP-Bold", bold, subfontIndex=idx))
            bold_name = "NotoSansJP-Bold"
            logger.info(f"Bold フォント登録成功 (subfontIndex={idx})")
        except Exception as e:
            logger.warning(f"Bold フォント登録失敗: {e}")

    return font_name, bold_name


def generate_pdf(topics: list[dict], used_model: str, output_path: str) -> None:
    font_name, bold_name = _register_fonts()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    period = f"{start_date.strftime('%Y/%m/%d')} 〜 {end_date.strftime('%Y/%m/%d')}"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    s = {
        "h1": ParagraphStyle("h1",
            fontName=bold_name, fontSize=22,
            textColor=HexColor("#202124"), spaceAfter=3),
        "period": ParagraphStyle("period",
            fontName=font_name, fontSize=10,
            textColor=HexColor("#5f6368"), spaceAfter=10),
        "topic_title": ParagraphStyle("topic_title",
            fontName=bold_name, fontSize=10,
            textColor=HexColor("#202124"), spaceAfter=2),
        "summary": ParagraphStyle("summary",
            fontName=font_name, fontSize=9,
            textColor=HexColor("#3c4043"), leading=14, spaceAfter=2),
        "url": ParagraphStyle("url",
            fontName=font_name, fontSize=8,
            textColor=HexColor("#1a73e8"), spaceAfter=6),
        "footer": ParagraphStyle("footer",
            fontName=font_name, fontSize=7,
            textColor=HexColor("#9aa0a6")),
    }

    story = []

    story.append(Paragraph("Weekly AI Report", s["h1"]))
    story.append(Paragraph(f"Period: {period}", s["period"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#dadce0")))
    story.append(Spacer(1, 6))

    # カテゴリ別にグループ化
    grouped: dict[str, list] = {cat: [] for cat in CATEGORY_ORDER}
    for topic in topics:
        cat = topic.get("category", "Other Notable Topics")
        grouped.setdefault(cat, []).append(topic)

    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue

        color = CATEGORY_COLORS[cat]
        label = CATEGORY_LABELS[cat]

        cat_style = ParagraphStyle(f"cat_{cat}",
            fontName=bold_name, fontSize=12,
            textColor=color, spaceBefore=14, spaceAfter=4)

        story.append(Paragraph(label, cat_style))
        story.append(HRFlowable(width="100%", thickness=0.8, color=color))
        story.append(Spacer(1, 4))

        for topic in items:
            title = topic.get("title", "(no title)")
            summary = topic.get("summary", "")
            url = topic.get("url", "")

            story.append(Paragraph(title, s["topic_title"]))
            if summary:
                story.append(Paragraph(summary, s["summary"]))
            if url:
                safe_url = url.replace("&", "&amp;")
                story.append(Paragraph(
                    f'<link href="{safe_url}" color="#1a73e8">{url}</link>',
                    s["url"],
                ))
            story.append(Spacer(1, 2))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#dadce0")))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"Model: {used_model}  |  Generated: {end_date.strftime('%Y/%m/%d %H:%M')} UTC",
        s["footer"],
    ))

    doc.build(story)
    logger.info(f"PDF 生成完了: {output_path}")
