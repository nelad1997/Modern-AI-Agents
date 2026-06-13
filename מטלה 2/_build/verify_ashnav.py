# -*- coding: utf-8 -*-
import json, os, sys
HERE = os.path.dirname(__file__)
t281 = json.load(open(os.path.join(HERE, "raw_ashnav.json"), encoding="utf-8"))["ashnav_281"]["text"]
tyod = json.load(open(os.path.join(HERE, "raw_ashnav.json"), encoding="utf-8"))["ashnav_yod"]["text"]
both = t281 + "\n" + tyod
terms = ["הורדוס", "נציב", "פרושים", "צדוקים", "איסיים", "המרד הגדול", "יבנה",
         "בגד", "תנאי עומר", "החסות", "גרשום", "חשמונא", "ראש הגולה", "גאונים",
         "סנהדרין", "קנאים", "אשכנז", "סעדיה"]
print("== presence in real ashnav_281+yod text ==")
for kw in terms:
    print(("Y" if kw in both else "n"), kw, both.count(kw))
