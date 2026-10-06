"""News NLP: topics, keywords, entities, sentiment, subjectivity, readability, summary (local, replaceable)."""
import re, math
from collections import Counter
STOP = set("a an the and or but if of to in on at for with by from as is are was were be been it its this that these those i we you they he she our your their there so than then not no do does did have has had will would can could should may might about into also just very more some what which who how when where why said says say after before over under new one two year years told per while his her him them their also according".split())
TOPICS = {
 "Politics": "government minister election parliament president policy vote party law senate court bill campaign opposition cabinet prime",
 "Business": "market company economy stock shares profit revenue bank inflation trade investors growth price earnings industry startup sales",
 "Technology": "technology software ai artificial intelligence app data cyber digital internet robot chip startup platform online device smartphone cloud",
 "Sports": "match team player cricket football tournament coach league win goal season championship score final stadium medal",
 "Health": "health hospital doctor patients disease vaccine virus treatment medical cancer cases outbreak medicine care",
 "Science": "research scientists study space climate species discovery earth satellite mission energy experiment laboratory",
 "Entertainment": "film movie actor actress music album festival series show director celebrity box office song award",
 "World": "war conflict border united nations foreign talks ceasefire sanctions diplomatic embassy refugees troops attack",
 "Education": "school students university exam college teachers education scholarship curriculum campus results admission",
 "Environment": "climate pollution flood rainfall emissions forest wildlife weather storm cyclone drought carbon",
}
POS = set("win wins won success growth improve improved improving boost gain gains rise rises record strong positive praise hope relief recovery breakthrough award celebrate benefit progress agreement peace safe launch support better best".split())
NEG = set("crisis death dead killed injured attack war fall falls fell drop loss losses decline fear risk threat crash fraud scandal protest flood fire collapse worst concern warns warning ban arrest violence cases shortage delay damage accused conflict".split())
NEGATE = {"not", "no", "never", "without", "hardly", "n't"}
SUBJ = set("shocking outrageous disastrous incredible terrible amazing stunning horrific brilliant massive slammed blasted devastating furious scandalous disgraceful miracle obviously clearly undoubtedly".split())

def sents(t): return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if len(s.split()) >= 4]
def toks(t): return [w for w in re.findall(r"[a-z][a-z'-]+", t.lower()) if w not in STOP and len(w) > 2]

def topics(text):
    t = Counter(toks(text)); sc = {k: sum(t[w] for w in v.split()) for k, v in TOPICS.items()}
    tot = sum(sc.values()); res = sorted(((k, v) for k, v in sc.items() if v), key=lambda x: -x[1])
    return [{"topic": k, "share": round(v * 100 / tot)} for k, v in res[:4]] or [{"topic": "General", "share": 100}]

def keywords(text, n=12):
    t = toks(text); c = Counter(t); c.update({f"{a} {b}": v * 1.8 for (a, b), v in Counter(zip(t, t[1:])).items() if v >= 2})
    return [w for w, _ in c.most_common(n)]

def entities(text):
    c = Counter()
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        e = m.group(1)
        if e.lower() not in STOP and len(e) > 2: c[e] += 1
    for m in re.finditer(r"\b([A-Z]{2,6})\b", text): c[m.group(1)] += 1
    return [{"name": k, "count": v} for k, v in c.most_common(10)]

def sentiment(text):
    out = []
    for s in sents(text):
        w = re.findall(r"[a-z']+", s.lower()); sc = 0
        for i, x in enumerate(w):
            v = 1 if x in POS else -1 if x in NEG else 0
            if v and any(p in NEGATE for p in w[max(0, i - 2):i]): v = -v
            sc += v
        out.append(sc)
    tot = sum(out); n = max(len(out), 1); score = round(max(-1, min(1, tot / (n * .8))), 2)
    return {"score": score, "label": "Positive" if score > .15 else "Negative" if score < -.15 else "Neutral",
            "positive_sentences": sum(x > 0 for x in out), "negative_sentences": sum(x < 0 for x in out), "neutral_sentences": sum(x == 0 for x in out)}

def subjectivity(text):
    w = re.findall(r"[a-z']+", text.lower()); n = max(len(w), 1)
    hits = sum(x in SUBJ for x in w); ex = text.count("!"); first = sum(x in ("i", "we", "my", "our") for x in w)
    s = min(100, round((hits * 6 + ex * 4 + first * 1.5) / n * 100 * 3))
    return {"score": s, "label": "Highly opinionated" if s > 40 else "Some opinion" if s > 15 else "Mostly factual"}

def readability(text):
    ss = sents(text); w = re.findall(r"[A-Za-z']+", text)
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", x.lower()))) for x in w)
    if not ss or not w: return {"score": 0, "level": "n/a"}
    f = 206.835 - 1.015 * len(w) / len(ss) - 84.6 * syl / len(w); f = round(max(0, min(100, f)))
    return {"score": f, "level": "Easy" if f >= 70 else "Standard" if f >= 50 else "Difficult"}

def summary(text, k=3):
    ss = sents(text)
    if len(ss) <= k: return " ".join(ss)
    kw = Counter(toks(text)); sc = []
    for i, s in enumerate(ss):
        t = toks(s); base = sum(kw[w] for w in t) / math.sqrt(len(t) or 1)
        sc.append((base * (1.6 if i == 0 else 1.2 if i < 3 else 1) * (1.15 if re.search(r"\d", s) else 1), i))
    return " ".join(ss[i] for _, i in sorted(sorted(sc, reverse=True)[:k], key=lambda x: x[1]))

def facts(text): return [s for s in sents(text) if re.search(r"\b\d[\d,.%]*\b", s)][:5]
def headline(text):
    s = sents(text); return (s[0] if s else text)[:110].rstrip(".")
def analyze(text):
    w = len(text.split())
    return {"headline": headline(text), "summary_short": summary(text, 2), "summary_long": summary(text, 5), "topics": topics(text), "keywords": keywords(text),
            "entities": entities(text), "sentiment": sentiment(text), "subjectivity": subjectivity(text), "readability": readability(text), "facts": facts(text),
            "words": w, "read_minutes": max(1, round(w / 220))}
