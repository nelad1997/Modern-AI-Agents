# -*- coding: utf-8 -*-
"""Scrape Hebrew Wikipedia (MediaWiki API) for the History bagrut syllabus.
Stores LOGICAL-order UTF-8 plaintext per article. Robust to rate limiting.
Merges into raw_wiki.json so re-runs only fetch what is still missing."""
import requests, json, time, os

UA = {"User-Agent": "EduRAG/1.0 (student project; contact: nelad1997 on GitHub)"}
API = "https://he.wikipedia.org/w/api.php"
S = requests.Session()
S.headers.update(UA)
HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "raw_wiki.json")

TITLES = [
    "לאומיות", "מדינת לאום", "אביב העמים", "איחוד איטליה", "איחוד גרמניה",
    "התנועה הרומנטית", "תנועת ההשכלה", "המהפכה הצרפתית", "נפוליאון בונפרטה",
    "המהפכה התעשייתית", "ועידת וינה", "ליברליזם",
    "ציונות", "בנימין זאב הרצל", "מדינת היהודים", "הקונגרס הציוני העולמי הראשון",
    "תוכנית אוגנדה", "אנטישמיות", "פרשת דרייפוס", "חיבת ציון", "אחד העם",
    "ההסתדרות הציונית", "תנועת ההשכלה היהודית",
    "העלייה הראשונה", "העלייה השנייה", "השומר", "אליעזר בן יהודה", "ניל\"י",
    "תל אביב", "הקיבוץ", "אחוזת בית", "גדוד העבודה",
    "הצהרת בלפור", "המנדט הבריטי", "תנועת העבודה הארץ ישראלית",
    "בית שני", "החשמונאים", "הורדוס", "המרד הגדול", "רבן יוחנן בן זכאי",
    "יבנה", "הסנהדרין", "בית המקדש השני", "מרד בר כוכבא", "הפרושים",
    "הצדוקים", "האיסיים", "פומפיוס", "יהודה הנשיא",
    "בגדאד", "הח'ליפות העבאסית", "בית החוכמה", "סעדיה גאון", "ד'ימי",
    "תנאי עומר", "רבנו גרשום", "יהדות אשכנז", "גזירות תתנ\"ו", "ריש גלותא",
    "ישיבות בבל", "הגאונים",
    "חיים וייצמן", "ועדת פיל", "יהדות ספרד", "גירוש ספרד",
    "משפטי נירנברג", "חסידי אומות העולם",
    "מלחמת העולם השנייה", "גרמניה הנאצית", "אדולף היטלר", "המפלגה הנאצית",
    "תורת הגזע הנאצית", "חוקי נירנברג", "ליל הבדולח", "גטו ורשה",
    "מרד גטו ורשה", "יודנראט", "הפתרון הסופי", "השואה",
    "אושוויץ", "קרב סטלינגרד", "פלישת נורמנדי", "הבריגדה היהודית",
    "יהדות צפון אפריקה בתקופת השואה", "ועידת ואנזה", "אקציה", "מרד מחנות ההשמדה",
    "הספר הלבן", "תנועת המרי העברי", "תוכנית החלוקה", "מלחמת העצמאות",
    "מגילת העצמאות", "העלייה ההמונית", "מעברה", "ההעפלה",
    "האו\"ם וההצבעה על תוכנית החלוקה", "דוד בן-גוריון", "ועדת אנגלו-אמריקאית",
    "מבצע יואב", "מדינת ישראל", "חוק השבות",
]

def fetch(title, retries=5):
    params = {"action": "query", "format": "json", "titles": title,
              "prop": "extracts", "explaintext": 1, "redirects": 1, "maxlag": 5}
    for attempt in range(retries):
        try:
            r = S.get(API, params=params, timeout=30)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                pages = r.json()["query"]["pages"]
                page = next(iter(pages.values()))
                return page.get("title", title), page.get("extract", ""), None
            reason = f"HTTP{r.status_code}"
        except Exception as e:
            reason = type(e).__name__
        time.sleep(1.5 * (attempt + 1))  # linear backoff
    return title, "", reason

def main():
    out = json.load(open(RAW, encoding="utf-8")) if os.path.exists(RAW) else {}
    todo = [t for t in TITLES if t not in out]
    print(f"Already have {len(out)}; fetching {len(todo)} missing.")
    missing = []
    for i, t in enumerate(todo, 1):
        real_title, text, err = fetch(t)
        if text:
            out[t] = {"resolved_title": real_title, "text": text,
                      "url": "https://he.wikipedia.org/wiki/" + t.replace(" ", "_")}
            print(f"[{i:02d}/{len(todo)}] {len(text):6d}  {t} -> {real_title}")
        else:
            missing.append(t)
            print(f"[{i:02d}/{len(todo)}] FAIL ({err})  {t}")
        json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.8)
    print(f"\nTotal saved: {len(out)}.  Still missing ({len(missing)}): {missing}")

if __name__ == "__main__":
    main()
