# -*- coding: utf-8 -*-
"""Grounding check: for each authored unit, measure how many of its content
words (Hebrew, len>=4) appear in the cited source text (Wikipedia article,
Yad Vashem page, or Campus ORT book chapter). Low overlap flags a unit whose
source_url may not actually support it."""
import json, os, re, sys
from urllib.parse import unquote, urlparse, parse_qs
sys.path.insert(0, os.path.dirname(__file__))
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

# --- corpus 1: Wikipedia (keyed by article title) ---
wiki = json.load(open(os.path.join(HERE, "raw_wiki.json"), encoding="utf-8"))
wiki_by_url = {}
for v in wiki.values():
    wiki_by_url[v["url"]] = v["text"]
    # also index by decoded title for robust lookup
    title = unquote(v["url"].split("/wiki/")[-1]).replace("_", " ")
    wiki_by_url[title] = v["text"]

# --- corpus 2: Yad Vashem (keyed by URL) ---
yv = json.load(open(os.path.join(HERE, "raw_yv.json"), encoding="utf-8"))
yv_by_url = {url: v["text"] for url, v in yv.items()}

# --- corpus 3: Campus ORT (keyed by book id + chapter id) ---
ort = json.load(open(os.path.join(HERE, "raw_ort.json"), encoding="utf-8"))

def resolve_source(url):
    """Return the source text for a unit's source_url, or ''. """
    if "wikipedia" in url:
        t = wiki_by_url.get(url)
        if t:
            return t
        title = unquote(url.split("/wiki/")[-1]).replace("_", " ")
        return wiki_by_url.get(title, "")
    if "yadvashem" in url:
        if url in yv_by_url:
            return yv_by_url[url]
        # tolerate trailing-slash / scheme variants
        for k, v in yv_by_url.items():
            if k.rstrip("/").endswith(url.split("yadvashem.org")[-1].rstrip("/")):
                return v
        return ""
    if "ort.org" in url:
        q = parse_qs(urlparse(url).query)
        bid = q.get("id", [""])[0]
        cid = q.get("chapterid", [""])[0]
        book = ort.get(bid, {})
        if cid:
            return book.get("chapters", {}).get(cid, "")
        return " ".join(book.get("chapters", {}).values())
    return ""

STOP = set("אשר אותו אותה אותם איזה אינו אינם היה היו הזה הזו הללו ועל ולא וכן זאת זהו יותר כאשר כדי כמו לאחר לפי מאוד מהם נגד עוד עליו עליהם רבים שכן שלא שלה שלו שלהם תחת בין גם כי על לא של זה זו הם הן את עם אל כל מן או אך עד".split())
WORD = re.compile(r"[א-ת]{4,}")

def content_words(text):
    return [w for w in WORD.findall(text) if w not in STOP]

rows = []
for ch, top, ku, ft, url, ashref in ALL_UNITS:
    art = resolve_source(url)
    words = content_words(ku + " " + ft)
    uniq = set(words)
    if not uniq or not art:
        rows.append((0.0, ch, ku, url, "NO ARTICLE" if not art else "NO WORDS"))
        continue
    hit = sum(1 for w in uniq if w in art)
    rows.append((hit / len(uniq), ch, ku, url, f"{hit}/{len(uniq)}"))

rows.sort()
avg = sum(r[0] for r in rows) / len(rows)
missing = sum(1 for r in rows if r[4] == "NO ARTICLE")
out = [f"units={len(rows)}  mean_overlap={avg:.2%}  no_article={missing}", "",
       "== LOWEST 20 (review candidates) =="]
for ov, ch, ku, url, frac in rows[:20]:
    tail = url.split("/wiki/")[-1] if "/wiki/" in url else url[-50:]
    out.append(f"{ov:5.0%}  [{frac:>7}]  ({ch}) {ku}  <- {tail}")
out.append("")
out.append("== distribution ==")
buckets = {"<30%": 0, "30-50%": 0, "50-70%": 0, ">=70%": 0}
for ov, *_ in rows:
    buckets["<30%" if ov < .3 else "30-50%" if ov < .5 else "50-70%" if ov < .7 else ">=70%"] += 1
out.append(str(buckets))
open(os.path.join(HERE, "_grounding.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:2]))
print("wrote _grounding.txt")
