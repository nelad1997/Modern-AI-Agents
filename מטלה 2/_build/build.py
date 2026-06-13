# -*- coding: utf-8 -*-
"""Build the two RAG data sources (+ combined master) from the existing
workbook plus the authored deep knowledge units. Hebrew cells are
right-aligned (readingOrder=2). Outputs into ../data/history_agent/.

מאגר_ידע is fully replaced by the deep 500-900 char units (units_p1..p7),
each carrying an ashnav_ref linking to its אשנב_פירוט_חומר sub_topic."""
import os, sys, openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(__file__))
from new_ashnav import NEW_ASHNAV
from units_p1 import UNITS_P1
from units_p2 import UNITS_P2
from units_p3 import UNITS_P3
from units_p4 import UNITS as UNITS_P4
from units_p5 import UNITS as UNITS_P5
from units_p6 import UNITS as UNITS_P6
from units_p7 import UNITS as UNITS_P7
from units_p8 import UNITS as UNITS_P8
from units_p9 import UNITS as UNITS_P9

ALL_UNITS = (list(UNITS_P1) + list(UNITS_P2) + list(UNITS_P3) + list(UNITS_P4)
             + list(UNITS_P5) + list(UNITS_P6) + list(UNITS_P7)
             + list(UNITS_P8) + list(UNITS_P9))

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "history_bagrut_master_3.xlsx")
OUT_DIR = os.path.join(HERE, "..", "..", "data", "history_agent")  # repo-root/data/history_agent
OUT_DIR = os.path.normpath(OUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)

HEADER_FILL = PatternFill("solid", fgColor="2F5496")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
CELL_FONT = Font(name="Arial", size=11)
RTL = Alignment(horizontal="right", vertical="top", wrap_text=True, readingOrder=2)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# practical per-column widths (chars)
WIDTHS = {
    "question_text": 55, "official_answer": 80, "grading_notes": 50, "source_url": 38,
    "required_content": 75, "full_text": 85, "knowledge_unit": 28, "sub_topic": 24,
    "section": 26, "required_curriculum_topics": 40, "required_knowledge_items": 45,
    "key_terms_expected": 38, "common_mistakes": 45, "question_topic": 34,
    "missing_knowledge": 40, "ashnav_ref": 30, "תיאור": 70, "גיליון": 22,
    "chapter": 16, "topic": 20,
}

# topic-level normalization (FIX 4): merge spelling variants
TOPIC_NORM = {
    "בגדד": "בגדאד",
}
CHAPTER_NORM = {"מלחמת העולם השנייה": "שואה"}

def read_sheet(wb, name):
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    return rows[0], [list(r) for r in rows[1:]]

def make_sheet(wb, title, header, rows):
    ws = wb.create_sheet(title)
    ws.sheet_view.rightToLeft = True
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    # style header
    for c in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True, readingOrder=2)
        cell.border = BORDER
        col = get_column_letter(c)
        ws.column_dimensions[col].width = WIDTHS.get(str(header[c - 1]), 18)
    # style data
    for r in range(2, len(rows) + 2):
        for c in range(1, len(header) + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = CELL_FONT
            cell.alignment = RTL
            cell.border = BORDER
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 26
    return ws

def main():
    wb_src = openpyxl.load_workbook(SRC)
    sheets = {}
    for name in ["שאלון_ומחוון", "אשנב_פירוט_חומר", "מאגר_ידע", "מיפוי_שאלה_לחומר", "מפתח"]:
        sheets[name] = read_sheet(wb_src, name)

    # --- אשנב_פירוט_חומר: existing + authored rows ---
    ash_header, ash_rows = sheets["אשנב_פירוט_חומר"]
    ash_rows += [list(r) for r in NEW_ASHNAV]
    st_idx = list(ash_header).index("sub_topic")
    ashnav_subtopics = {str(r[st_idx]).strip() for r in ash_rows if r[st_idx]}

    # --- מאגר_ידע: fully replaced by the deep units (6-tuple incl. ashnav_ref) ---
    kb_header = ["chapter", "topic", "knowledge_unit", "full_text", "source_url", "ashnav_ref"]
    kb_rows = []
    for ch, topic, ku, full_text, url, ashref in ALL_UNITS:
        ch = CHAPTER_NORM.get(ch, ch)
        topic = TOPIC_NORM.get(topic, topic)
        ashref = ashref if ashref in ashnav_subtopics else "כללי"
        kb_rows.append([ch, topic, ku, full_text, url, ashref])

    # --- update מיפוי_שאלה_לחומר coverage ---
    map_header, map_rows = sheets["מיפוי_שאלה_לחומר"]
    H = {h: i for i, h in enumerate(map_header)}
    def setrow(yt, qn, **kw):
        for r in map_rows:
            if r[H["year_term"]] == yt and str(r[H["question_num"]]) == qn:
                for k, v in kw.items():
                    r[H[k]] = v
                return True
        return False
    # 3 Hasmonean rows now covered by new units
    for yt, qn in [('קיץ תשע"ט', '2'), ('חורף תש"ף', '2'), ('קיץ תש"ף', '1')]:
        setrow(yt, qn, coverage_status="מכוסה", missing_knowledge=None,
               required_knowledge_items="הממלכה החשמונאית › הלניזציה מול הצביון היהודי; התרחבות טריטוריאלית ומדיניות הגיור; הזרמים בעם (פרושים/צדוקים)")
    # 2 Baghdad/ערים rows – map and mark covered
    setrow('חורף תש"ף', '5',
           question_topic="מעמד בני החסות – תנאי עומר וגורמי ההמשכיות היהודית תחת האסלאם",
           required_curriculum_topics="ערים וקהילות › מעמד בני החסות › תנאי עומר",
           required_knowledge_items="מעמד הד'ימי; תנאי עומר וההגבלות; הקהילה כמסגרת אוטונומית",
           key_terms_expected="ד'ימי, תנאי עומר, ג'יזיה, אהל אל-כתאב, אוטונומיה קהילתית",
           common_mistakes="בלבול בין החובות (ג'יזיה, הגבלות) למטרתן; התעלמות מגורמי ההמשכיות (אוטונומיה, חופש דת)",
           coverage_status="מכוסה", missing_knowledge=None)
    setrow('קיץ תש"ף', '5',
           question_topic="צמיחת הערים בח'ליפות המוסלמית והמבנה החברתי-העירוני",
           required_curriculum_topics="ערים וקהילות › העיר המוסלמית › צמיחת הערים ובגדאד",
           required_knowledge_items="ייסוד בגדאד ושיקוליו; בגדאד כמרכז סחר; המבנה החברתי בעיר",
           key_terms_expected="ח'ליפות עבאסית, בגדאד, רבעים, מרכז סחר, מבנה חברתי",
           common_mistakes="אי-קישור בין הגורמים הכלכליים-מנהליים לייסוד הערים; התעלמות ממשמעות החלוקה לרבעים",
           coverage_status="מכוסה", missing_knowledge=None)

    qm_header, qm_rows = sheets["שאלון_ומחוון"]

    # --- rebuild מפתח ---
    key_header = ("גיליון", "תיאור", "כמות")
    key_rows = [
        ["שאלון_ומחוון", "זוגות שאלה+תשובה רשמית מ-9 מועדים (022281 + 022261), עם מטלות, ניקוד והנחיות בדיקה. קישור ישיר למחוון בכל שורה.", len(qm_rows)],
        ["אשנב_פירוט_חומר", "פירוט החומר הנדרש לכל נושא לפי האשנ\"בים הרשמיים, ברזולוציית תת-נושא. קישור ישיר לאשנ\"ב בכל שורה.", len(ash_rows)],
        ["מאגר_ידע", "יחידות ידע מעמיקות (500-900 תווים) המכסות את מלוא הסילבוס של שני השאלונים. מקורות: קמפוס ORT, יד ושם, ויקיפדיה. עמודת ashnav_ref מקשרת כל יחידה לתת-הנושא באשנ\"ב.", len(kb_rows)],
        ["מיפוי_שאלה_לחומר", "מיפוי כל שאלה לחומר הנדרש, מונחי מפתח, טעויות נפוצות ומצב כיסוי במאגר.", len(qm_rows)],
    ]

    def build(path, sheet_specs):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for title, header, rows in sheet_specs:
            make_sheet(wb, title, header, rows)
        wb.save(path)
        size = os.path.getsize(path)
        print(f"  {os.path.basename(path)}: {size/1024:.1f} KB | sheets={[s[0] for s in sheet_specs]}")

    print("Building outputs ->", OUT_DIR)
    # Source 1 — marking schemes (validation / answer key)
    build(os.path.join(OUT_DIR, "source1_marking_schemes.xlsx"), [
        ("שאלון_ומחוון", qm_header, qm_rows),
        ("מיפוי_שאלה_לחומר", map_header, map_rows),
    ])
    # Source 2 — curriculum knowledge base (verification)
    build(os.path.join(OUT_DIR, "source2_knowledge_base.xlsx"), [
        ("אשנב_פירוט_חומר", ash_header, ash_rows),
        ("מאגר_ידע", kb_header, kb_rows),
    ])
    # Combined master
    build(os.path.join(OUT_DIR, "history_bagrut_master.xlsx"), [
        ("שאלון_ומחוון", qm_header, qm_rows),
        ("אשנב_פירוט_חומר", ash_header, ash_rows),
        ("מאגר_ידע", kb_header, kb_rows),
        ("מיפוי_שאלה_לחומר", map_header, map_rows),
        ("מפתח", key_header, key_rows),
    ])
    print(f"\nCounts: שאלון_ומחוון={len(qm_rows)}, אשנב={len(ash_rows)}, "
          f"מאגר_ידע={len(kb_rows)}, מיפוי={len(map_rows)}")

if __name__ == "__main__":
    main()
