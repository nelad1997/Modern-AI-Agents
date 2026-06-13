# -*- coding: utf-8 -*-
"""Scrape Campus ORT 'תקציר ידע' books from the public course
'היסטוריה לבגרות' (course id=79). Each Moodle book has a public print view
(mod/book/tool/print/index.php?id=N) with the whole book, and a normal view
whose TOC maps chapterid -> chapter title, so units can cite the SPECIFIC
chapter URL (mod/book/view.php?id=N&chapterid=C).
Stores raw_ort.json: {book_id: {title, section, toc: {chapterid: title},
chapters: {chapterid: text}, url}}."""
import requests, json, time, os, re, sys, urllib3, html as ihtml

urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EduRAG/1.0 (student project; contact: nelad1997 on GitHub)"}
S = requests.Session(); S.headers.update(UA)
HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw_ort.json")

BOOKS = {
    "8124": "מלחמת העולם השנייה והשואה",
    "8164": "לאומיות וציונות",
    "8167": "לאומיות וציונות",
    "8170": "לאומיות וציונות",
    "8173": "לאומיות וציונות",
    "8176": "לאומיות וציונות",
    "8245": "בונים את מדינת ישראל במזרח התיכון",
    "8270": "סוגיות נבחרות בתולדות מדינת ישראל",
}

TAG = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)

def clean(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = ihtml.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def get(url):
    for attempt in range(3):
        try:
            r = S.get(url, timeout=30, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return ""

def toc_map(book_id):
    """chapterid -> title from the normal book view's TOC."""
    htm = get(f"https://campus.ort.org.il/mod/book/view.php?id={book_id}")
    pairs = re.findall(
        r"view\.php\?id=" + book_id + r"&(?:amp;)?chapterid=(\d+)[^>]*>\s*([^<]+)<", htm)
    toc = {}
    for cid, title in pairs:
        title = clean(title)
        if title and cid not in toc:
            toc[cid] = title
    return toc

def chapters_from_print(book_id):
    """Split the print view into chapters. Moodle print view marks each
    chapter with <div class="book_chapter" id="ch{chapterid}">… or h2 titles."""
    htm = get(f"https://campus.ort.org.il/mod/book/tool/print/index.php?id={book_id}")
    htm = TAG.sub(" ", htm)
    # try split on chapter anchors
    chunks = re.split(r'<div[^>]*id="ch(\d+)"', htm)
    out = {}
    if len(chunks) > 2:
        # chunks: [pre, cid1, body1, cid2, body2, ...]
        for i in range(1, len(chunks) - 1, 2):
            cid, body = chunks[i], chunks[i + 1]
            paras = [clean(p) for p in re.findall(
                r"<(?:p|h1|h2|h3|h4|li|td|blockquote)[^>]*>(.*?)</(?:p|h1|h2|h3|h4|li|td|blockquote)>",
                body, re.S)]
            text = "\n".join(p for p in paras if len(p) > 15 and re.search(r"[א-ת]", p))
            out[cid] = text
    else:
        paras = [clean(p) for p in re.findall(
            r"<(?:p|h1|h2|h3|h4|li|td|blockquote)[^>]*>(.*?)</(?:p|h1|h2|h3|h4|li|td|blockquote)>",
            htm, re.S)]
        out["all"] = "\n".join(p for p in paras if len(p) > 15 and re.search(r"[א-ת]", p))
    return out

def main():
    out = json.load(open(RAW, encoding="utf-8")) if os.path.exists(RAW) else {}
    for bid, section in BOOKS.items():
        if bid in out:
            continue
        toc = toc_map(bid)
        chs = chapters_from_print(bid)
        total = sum(len(t) for t in chs.values())
        out[bid] = {
            "section": section,
            "toc": toc,
            "chapters": chs,
            "url": f"https://campus.ort.org.il/mod/book/view.php?id={bid}",
        }
        print(f"book {bid} ({section}): {len(toc)} toc, {len(chs)} chapters, {total} chars")
        json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.8)
    print(f"Total books: {len(out)}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
