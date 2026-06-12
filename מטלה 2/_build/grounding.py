# -*- coding: utf-8 -*-
"""Grounding check: for each authored unit, measure how many of its content
words (Hebrew, len>=4) appear in the cited Wikipedia article text. Low overlap
flags a unit whose source_url may not actually support it."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from new_units import NEW_UNITS

HERE = os.path.dirname(__file__)
d = json.load(open(os.path.join(HERE, "raw_wiki.json"), encoding="utf-8"))
url2text = {v["url"]: v["text"] for v in d.values()}

STOP = set("אשר אותו אותה אותם איזה אינו אינם היה היו הזה הזו הללו ועל ולא וכן זאת זהו יותר כאשר כדי כמו לאחר לפי מאוד מהם נגד עוד עליו עליהם רבים שכן שלא שלה שלו שלהם תחת בין גם כי על לא של זה זו הם הן את עם אל כל מן או אך עד".split())
WORD = re.compile(r"[א-ת]{4,}")

def content_words(text):
    return [w for w in WORD.findall(text) if w not in STOP]

rows = []
for ch, top, ku, ft, url in NEW_UNITS:
    art = url2text.get(url, "")
    words = content_words(ku + " " + ft)
    uniq = set(words)
    if not uniq or not art:
        rows.append((0.0, ch, ku, url, "NO ARTICLE" if not art else "NO WORDS"))
        continue
    hit = sum(1 for w in uniq if w in art)
    rows.append((hit / len(uniq), ch, ku, url, f"{hit}/{len(uniq)}"))

rows.sort()
avg = sum(r[0] for r in rows) / len(rows)
out = [f"units={len(rows)}  mean_overlap={avg:.2%}", "", "== LOWEST 20 (review candidates) =="]
for ov, ch, ku, url, frac in rows[:20]:
    out.append(f"{ov:5.0%}  [{frac:>7}]  ({ch}) {ku}  <- {url.split('/wiki/')[-1]}")
out.append("")
out.append("== distribution ==")
buckets = {"<30%": 0, "30-50%": 0, "50-70%": 0, ">=70%": 0}
for ov, *_ in rows:
    buckets["<30%" if ov < .3 else "30-50%" if ov < .5 else "50-70%" if ov < .7 else ">=70%"] += 1
out.append(str(buckets))
open(os.path.join(HERE, "_grounding.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:2]))
print("wrote _grounding.txt")
