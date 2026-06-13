# -*- coding: utf-8 -*-
"""Download official Ministry of Education ashnav (אשנ"ב) PDFs and extract
LOGICAL-order Hebrew text. NOTE: plain PyMuPDF get_text already returns correct
logical order for these PDFs — applying python-bidi/get_display or reversing
lines CORRUPTS it. So we store the plain text as-is. Government content = public.
Saves per-PDF text to _build/raw_ashnav.json."""
import requests, json, os, fitz

UA = {"User-Agent": "EduRAG/1.0 (student project; contact: nelad1997 on GitHub)"}
HERE = os.path.dirname(__file__)
PDF_DIR = os.path.join(HERE, "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

PDFS = {
    "ashnav_281": "https://meyda.education.gov.il/files/Pop/0files/historya/pedagogia/tohnit-halofot/ashnab_281_tashat.pdf",
    "ashnav_yod": "https://meyda.education.gov.il/files/Pop/0files/historya/pedagogia/tohnit-halofot/ashnav-yod-tshap-a.pdf",
    "ashnav_261": "https://meyda.education.gov.il/files/Pop/0files/historya/pedagogia/tohnit-halofot/022261.pdf",
}

def extract(path):
    doc = fitz.open(path)
    # plain extraction -> already logical order for these RTL PDFs
    return "\n\n".join(page.get_text("text") for page in doc)

def main():
    out = {}
    for key, url in PDFS.items():
        local = os.path.join(PDF_DIR, key + ".pdf")
        if not os.path.exists(local):
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            open(local, "wb").write(r.content)
            print(f"downloaded {key} ({len(r.content)} bytes)")
        text = extract(local)
        out[key] = {"url": url, "text": text}
        open(os.path.join(HERE, f"_ashnav_{key}.txt"), "w", encoding="utf-8").write(text)
        print(f"{key}: {len(text)} chars")
    json.dump(out, open(os.path.join(HERE, "raw_ashnav.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("saved raw_ashnav.json (logical order)")

if __name__ == "__main__":
    main()
