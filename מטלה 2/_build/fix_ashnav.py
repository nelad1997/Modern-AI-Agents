# -*- coding: utf-8 -*-
"""Re-extract the ashnav PDFs converting PyMuPDF visual-order RTL output to
LOGICAL order. Strategy: reverse each line (recovers Hebrew logical order),
then restore embedded LTR runs (digits/Latin/URLs) back to their reading order."""
import os, re, json, fitz

HERE = os.path.dirname(__file__)
PDF_DIR = os.path.join(HERE, "pdfs")

HEB = re.compile(r'[֐-׿]')
# an LTR token = run of latin/digits and the punctuation that binds them
LTR_RUN = re.compile(r'[0-9A-Za-z][0-9A-Za-z./:%_\-]*')

def visual_to_logical(line):
    if not HEB.search(line):
        return line  # pure latin/number line – leave as-is
    rev = line[::-1]                       # reverse whole line -> Hebrew now logical
    rev = LTR_RUN.sub(lambda m: m.group(0)[::-1], rev)  # un-reverse latin/number runs
    return rev

def extract(path):
    doc = fitz.open(path)
    out = []
    for page in doc:
        raw = page.get_text("text")
        out.append("\n".join(visual_to_logical(l) for l in raw.split("\n")))
    return "\n\n".join(out)

def main():
    res = {}
    for key in ["ashnav_281", "ashnav_yod", "ashnav_261"]:
        p = os.path.join(PDF_DIR, key + ".pdf")
        if not os.path.exists(p):
            print("missing", p); continue
        txt = extract(p)
        res[key] = txt
        # sample for eyeballing
        open(os.path.join(HERE, f"_ashnav_fixed_{key}.txt"), "w", encoding="utf-8").write(txt)
        print(key, len(txt), "chars")
    json.dump({k: {"text": v} for k, v in res.items()},
              open(os.path.join(HERE, "raw_ashnav_fixed.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
