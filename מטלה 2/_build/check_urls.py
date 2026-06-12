# -*- coding: utf-8 -*-
"""Check every source_url in the built master workbook resolves (HTTP 200).
requests encodes non-ASCII (Hebrew) paths automatically; a 200 confirms the
readable Hebrew URL is valid in practice."""
import openpyxl, requests, time, os, sys
from collections import OrderedDict

MASTER = os.path.join(os.path.dirname(__file__), "..", "..", "data", "history_agent",
                      "history_bagrut_master.xlsx")
UA = {"User-Agent": "EduRAG/1.0 (student project; contact: nelad1997 on GitHub)"}
S = requests.Session(); S.headers.update(UA)

def collect():
    wb = openpyxl.load_workbook(MASTER, read_only=True)
    urls = OrderedDict()
    for name in ["שאלון_ומחוון", "אשנב_פירוט_חומר", "מאגר_ידע"]:
        ws = wb[name]
        rows = list(ws.iter_rows(values_only=True))
        hdr = rows[0]
        idx = hdr.index("source_url")
        for r in rows[1:]:
            u = r[idx]
            if u:
                urls.setdefault(u, 0)
                urls[u] += 1
    return urls

def check(u):
    try:
        r = S.get(u, timeout=25, allow_redirects=True)
        return r.status_code
    except Exception as e:
        return type(e).__name__

def main():
    urls = collect()
    print(f"unique source_urls: {len(urls)}")
    bad = []
    for i, u in enumerate(urls, 1):
        code = check(u)
        ok = (code == 200)
        if not ok:
            bad.append((u, code))
        print(f"[{i:03d}/{len(urls)}] {code}  (x{urls[u]})  {u}")
        time.sleep(0.25)
    print(f"\nNON-200 ({len(bad)}):")
    for u, c in bad:
        print(f"  {c}  {u}")
    open(os.path.join(os.path.dirname(__file__), "_bad_urls.txt"), "w", encoding="utf-8").write(
        "\n".join(f"{c}\t{u}" for u, c in bad))

if __name__ == "__main__":
    main()
