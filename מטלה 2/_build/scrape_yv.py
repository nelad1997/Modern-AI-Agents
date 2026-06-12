# -*- coding: utf-8 -*-
"""Scrape Yad Vashem Hebrew educational pages for the History bagrut KB.
Two collections:
  1. lomdim-labagrut content pages (4 categories, discovered via sitemap-he.xml)
  2. /he/holocaust/about/ topical encyclopedia pages
NOTE: local environment fails TLS verification for yadvashem.org (missing
intermediate cert in local store) -> verify=False on purpose, read-only fetch
of public educational pages. Stores plain text per URL in raw_yv.json."""
import requests, json, time, os, re, sys, urllib3

urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EduRAG/1.0 (student project; contact: nelad1997 on GitHub)"}
S = requests.Session(); S.headers.update(UA)
HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw_yv.json")

LOMDIM = [
    # nazi-ideology 1-6
    *[f"https://www.yadvashem.org/he/education/lomdim-labagrut/nazi-ideology/nazi-ideology-{i}.html" for i in range(1, 7)],
    # beginning-of-the-persecution / world-war-two 1-5
    *[f"https://www.yadvashem.org/he/education/lomdim-labagrut/beginning-of-the-persecution/world-war-two-{i}.html" for i in range(1, 6)],
    # murder-final-solution / final-solution 1-5
    *[f"https://www.yadvashem.org/he/education/lomdim-labagrut/murder-final-solution/final-solution-{i}.html" for i in range(1, 6)],
    # consequences 1-4
    *[f"https://www.yadvashem.org/he/education/lomdim-labagrut/consequences/consequences-{i}.html" for i in range(1, 5)],
]

ABOUT = [
    "https://www.yadvashem.org/he/holocaust/about/" + p for p in [
        "what-was-the-holocaust.html",
        "nazi-germany-1933-39.html",
        "nazi-germany-1933-39/antisemitism.html",
        "nazi-germany-1933-39/beginning-of-persecution.html",
        "nazi-germany-1933-39/1938.html",
        "nazi-germany-1933-39/non-jewish-victims.html",
        "outbreak-of-ww2-anti-jewish-policy.html",
        "outbreak-of-ww2-anti-jewish-policy/conquest-of-poland.html",
        "outbreak-of-ww2-anti-jewish-policy/german-conquests.html",
        "outbreak-of-ww2-anti-jewish-policy/western-europe.html",
        "outbreak-of-ww2-anti-jewish-policy/south-eastern-europe.html",
        "outbreak-of-ww2-anti-jewish-policy/north-africa-and-middle-east.html",
        "ghettos.html",
        "ghettos/daily-life.html",
        "ghettos/warsaw.html",
        "ghettos/lodz.html",
        "ghettos/theresienstadt.html",
        "final-solution-beginning.html",
        "final-solution-beginning/mass-murder-in-ussr.html",
        "final-solution-beginning/wannsee-conference.html",
        "final-solution-beginning/baltic-states.html",
        "final-solution-beginning/romania-jews-murder.html",
        "final-solution.html",
        "final-solution/auschwitz.html",
        "final-solution/death-camps.html",
        "final-solution/deportation.html",
        "camps.html",
        "camps/labor-concentration-camps.html",
        "camps/daily-life.html",
        "combat-resistance.html",
        "combat-resistance/warsaw-ghetto.html",
        "combat-resistance/jewish-armed-resistance.html",
        "combat-resistance/human-spirit.html",
        "combat-resistance/jewish-soldiers.html",
        "fate-of-jews.html",
        "fate-of-jews/poland.html",
        "fate-of-jews/hungary.html",
        "fate-of-jews/western-europe.html",
        "fate-of-jews/balkans-and-slovakia.html",
        "rescue.html",
        "rescue/righteous.html",
        "rescue/rescue-by-jews.html",
        "rescue/worlds-reaction.html",
        "end-of-war-aftermath.html",
        "end-of-war-aftermath/last-months.html",
        "end-of-war-aftermath/liberation.html",
        "end-of-war-aftermath/nuremberg-trials.html",
        "end-of-war-aftermath/ghettos-camps.html",
    ]
]

TAG = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.S | re.I)
BLOCK = re.compile(r"<(?:p|h1|h2|h3|h4|li|blockquote)[^>]*>(.*?)</(?:p|h1|h2|h3|h4|li|blockquote)>", re.S | re.I)

def html_to_text(htm):
    htm = TAG.sub(" ", htm)
    parts = []
    for m in BLOCK.finditer(htm):
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"&nbsp;?", " ", t)
        t = re.sub(r"&quot;?", '"', t)
        t = re.sub(r"&amp;?", "&", t)
        t = re.sub(r"&#\d+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        # keep Hebrew-bearing lines only, skip nav/boilerplate
        if len(t) > 25 and re.search(r"[א-ת]", t):
            parts.append(t)
    # dedupe consecutive repeats
    out, prev = [], None
    for p in parts:
        if p != prev:
            out.append(p)
        prev = p
    return "\n".join(out)

def title_of(htm):
    m = re.search(r"<title>([^<|]+)", htm)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            r = S.get(url, timeout=30, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return ""

def main():
    out = json.load(open(RAW, encoding="utf-8")) if os.path.exists(RAW) else {}
    todo = [u for u in LOMDIM + ABOUT if u not in out]
    print(f"Already have {len(out)}; fetching {len(todo)}.")
    for i, u in enumerate(todo, 1):
        htm = fetch(u)
        if not htm:
            print(f"[{i:02d}/{len(todo)}] FAIL  {u}")
            continue
        text = html_to_text(htm)
        out[u] = {"title": title_of(htm), "text": text, "url": u}
        print(f"[{i:02d}/{len(todo)}] {len(text):6d}  {u.split('/he/')[-1]}")
        json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.6)
    print(f"\nTotal saved: {len(out)}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
