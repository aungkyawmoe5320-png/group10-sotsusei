import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

FONT_NAME = "IPAexGothic"
FONT_PATH = Path(__file__).resolve().parent / "fonts" / "ipaexg.ttf"
_font_ready = False


def _register_font():
    """日本語フォントを、PDFに埋め込む形で登録する（1回だけ）。"""
    global _font_ready
    if not _font_ready:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        _font_ready = True


def _style(name, size, leading, **kw):
    # wordWrap="CJK": 日本語は、スペースがなくても、行の端で折り返す
    return ParagraphStyle(name, fontName=FONT_NAME, fontSize=size, leading=leading, wordWrap="CJK", **kw)


def build_pdf(title, updated, sections, signature=""):
    """まとめPDFを作り、PDFファイルの中身（bytes）を返す。"""
    _register_font()
    brand = _style("brand", 9, 12, alignment=1, textColor=colors.grey)
    h1 = _style("h1", 18, 26, alignment=1)
    small = _style("small", 9, 13, alignment=1, textColor=colors.grey)
    h2 = _style("h2", 12, 18, textColor=colors.HexColor("#198754"), spaceBefore=10, spaceAfter=3)
    body = _style("body", 10, 15)
    item = _style("item", 10, 15, leftIndent=12, bulletIndent=2)
    right = _style("right", 9, 13, alignment=2, textColor=colors.grey, spaceBefore=12)

    story = [
        Paragraph("みまもりケアリンク", brand),
        Paragraph(escape(title), h1),
        Paragraph(f"最終更新日 {updated}", small),
        Spacer(1, 4),
        HRFlowable(width="100%", color=colors.lightgrey),
    ]
    for s in sections:
        block = [Paragraph(escape(s["heading"]), h2)]
        if s.get("text"):
            block.append(Paragraph(escape(s["text"]), body))
        for d in s.get("details", []):
            block.append(Paragraph(escape(d), item, bulletText="•"))
        story.append(KeepTogether(block))  # 見出しと中身が、ページの境目で分かれないようにする
    if signature:
        story.append(Paragraph(f"署名: {escape(signature)}", right))

    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                      title=title, author="みまもりケアリンク").build(story)
    return buffer.getvalue()
