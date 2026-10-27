"""r/DupuytrenDisease mentions, via the Arctic Shift Reddit archive (reddit.com blocks cloud IPs).

1. Download every post and comment in the subreddit (cached as JSONL in data/cache, not committed).
2. For each clinician listing, find mentions of "Dr <Lastname>" or the full name.
3. A mention that names a treatment in the same sentence becomes "patient_reported" evidence for that treatment.
4. Doctors that patients mention often but that no list has are written to data/build/reddit_unmatched.json
   for manual review (we never auto-create listings from Reddit).
Only short snippets and permalinks are kept; usernames are dropped.
"""
import collections
import json
import os
import re
import time

from lib import CACHE, http_json, strip_accents

API = "https://arctic-shift.photon-reddit.com/api/{kind}/search"
SUB = "DupuytrenDisease"
TX_TERMS = [
    ("radiotherapy", r"radiat|radiother|\brt\b|x-?ray treatment|orthovoltage|electron beam|rad onc"),
    ("steroid_injection", r"steroid|kenalog|triamcinolone|cortisone|depo-?medrol|\bshots?\b|injection"),
    ("needle_aponeurotomy", r"\bneedl|\bna\b|\bpnf\b|aponeurotomy|fasciotomy|needling"),
    ("collagenase", r"xiaflex|xiapex|collagenase"),
    ("fasciectomy", r"fasciectomy|surgery|operat|open release"),
    ("hyaluronidase_injection", r"vitrase|hyaluronidase|hylenex"),
    ("cryoablation", r"\bcryo"),
]
FOOT = re.compile(r"ledderhose|\bfeet\b|\bfoot\b|plantar|sole|podiatr", re.I)
HAND = re.compile(r"\bhand|finger|palm|dupuytren|\bdd\b", re.I)
STOP_SURNAMES = {"google", "reddit", "youtube", "who", "the", "my", "said", "told", "says"}
# For these, a bare "Dr <surname>" is too ambiguous; we need the full name or the listing's town nearby.
COMMON_SURNAMES = set("""smith jones brown johnson miller davis wilson taylor anderson thomas moore martin lee white harris
clark lewis young hall allen king scott green baker adams nelson hill campbell mitchell roberts carter phillips evans
turner parker collins edwards stewart morris murphy cook rogers morgan cooper peterson reed bailey kelly howard cox ward
richardson wood watson brooks bennett gray grey james hughes price myers long foster sanders ross powell jenkins perry russell
sullivan bell coleman butler henderson barnes fisher patel khan rose chen wang kim park singh ali ahmed west little
jackson walker wright lopez gonzalez garcia martinez robinson hernandez stone fox black dean""".split())


def _cache_path(kind):
    return os.path.join(CACHE, f"reddit_{kind}.jsonl")


def download(kind):
    """kind = posts | comments. Incremental: resumes after the newest cached item."""
    path = _cache_path(kind)
    items = {}
    if os.path.exists(path):
        for line in open(path):
            x = json.loads(line)
            items[x["id"]] = x
    after = max((x["created_utc"] for x in items.values()), default=1262304000)
    fields = "id,created_utc,title,selftext,score" if kind == "posts" else \
        "id,created_utc,body,link_id,score"
    while True:
        res = http_json(API.format(kind=kind), {"subreddit": SUB, "limit": 100, "sort": "asc",
                                               "after": int(after), "fields": fields},
                        headers={"User-Agent": "curl/8.5.0"})
        data = res.get("data") or []
        new = [d for d in data if d["id"] not in items]
        for d in data:
            items[d["id"]] = d
        if not data or not new:
            break
        after = max(d["created_utc"] for d in data)
        time.sleep(0.4)
    with open(path + ".tmp", "w") as f:
        for x in sorted(items.values(), key=lambda x: x["created_utc"]):
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    os.replace(path + ".tmp", path)
    return list(items.values())


def _docs():
    posts = download("posts")
    comments = download("comments")
    docs = []
    for p in posts:
        docs.append({"id": p["id"], "t": p["created_utc"], "text": f"{p.get('title') or ''}\n{p.get('selftext') or ''}",
                     "url": f"https://www.reddit.com/r/{SUB}/comments/{p['id']}/", "kind": "post"})
    for c in comments:
        post = (c.get("link_id") or "").replace("t3_", "")
        docs.append({"id": c["id"], "t": c["created_utc"], "text": c.get("body") or "",
                     "url": f"https://www.reddit.com/r/{SUB}/comments/{post}/comment/{c['id']}/", "kind": "comment"})
    return [d for d in docs if d["text"] and d["text"] not in ("[deleted]", "[removed]")], len(posts), len(comments)


def _sentence(text, start, end):
    a = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    bs = [i for i in (text.find(".", end), text.find("\n", end), text.find("!", end), text.find("?", end)) if i != -1]
    b = min(bs) if bs else len(text)
    return text[a + 1:b + 1].strip()


def _snippet(text, start, end, width=110):
    a, b = max(0, start - width), min(len(text), end + width)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a else "") + s + ("…" if b < len(text) else "")


def _edits(a, b):
    """Levenshtein distance, for catching patients' misspellings of long surnames."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _variants(last, titled):
    """Spellings seen after "Dr" in the archive within two edits of a long, distinctive surname."""
    last = last.lower()
    if len(last) < 7:
        return []
    return sorted(t for t in titled if t != last and t[:2] == last[:2] and abs(len(t) - len(last)) <= 2
                  and _edits(t, last) <= (2 if len(last) >= 9 else 1))


def _patterns(name, variants=()):
    toks = [t for t in re.split(r"\s+", name.replace(".", " ")) if t]
    last = toks[-1]
    if len(last) < 3 or last.lower() in STOP_SURNAMES:
        return None
    first = toks[0] if len(toks) > 1 and len(toks[0]) > 1 else None
    lasts = "|".join(re.escape(x) for x in [last, *variants])
    pats = [rf"\b(?:dr\.?|doctor|prof\.?|professor|mr\.?|ms\.?)\s+(?:{lasts})\b"]
    if first:
        pats.append(rf"\b{re.escape(first)}\s+(?:[A-Z]\.?\s+)?{re.escape(last)}\b")
    return re.compile("|".join(pats), re.I)


def run(listings):
    docs, n_posts, n_comments = _docs()
    print(f"reddit: {n_posts} posts, {n_comments} comments in archive")
    folded = [(d, strip_accents(d["text"])) for d in docs]
    surname_count = collections.Counter(strip_accents(m["name"]).replace(".", " ").split()[-1].lower()
                                        for m in listings if m["kind"] == "clinician")
    titled = {m.group(1).lower() for _, text in folded
              for m in re.finditer(r"\b(?:Dr\.?|Doctor|Prof\.?)\s+(?:[A-Z][a-z]+\s+)?([A-Z][a-zA-Z'\-]{6,})", text)}
    matched_spans = collections.defaultdict(set)
    total = 0
    for m in listings:
        if m["kind"] != "clinician":
            continue
        last = strip_accents(m["name"]).replace(".", " ").split()[-1].lower()
        variants = [v for v in _variants(last, titled) if v not in surname_count]
        rx = _patterns(strip_accents(m["name"]), variants)
        if not rx:
            continue
        first = strip_accents(m["name"]).replace(".", " ").split()[0].lower()
        strict = last in COMMON_SURNAMES or surname_count[last] > 1
        places = {strip_accents(l.get("city") or "").lower() for l in m["locations"]} - {""}
        mentions = []
        for d, text in folded:
            for hit in rx.finditer(text):
                if strict:
                    low = text.lower()
                    if not (re.search(rf"\b{re.escape(first)}\b", low) and len(first) > 1) and \
                            not any(p in low for p in places):
                        continue
                matched_spans[d["id"]].add(hit.group(0).lower())
                sent = _sentence(text, hit.start(), hit.end())
                tx = [code for code, pat in TX_TERMS if re.search(pat, sent, re.I)]
                site = "foot" if FOOT.search(sent) and not HAND.search(sent) else "hand"
                mentions.append({"id": d["id"], "url": d["url"], "date": time.strftime("%Y-%m-%d", time.gmtime(d["t"])),
                                 "snippet": _snippet(d["text"], hit.start(), hit.end()), "treatments": tx,
                                 "site": site})
                break
        if not mentions:
            continue
        mentions.sort(key=lambda x: x["date"], reverse=True)
        total += 1
        m["reddit"] = {"count": len(mentions), "mentions": mentions[:12]}
        for x in mentions:
            for code in x["treatments"]:
                key = f"{code}:{x['site']}"
                ev = {"source": "reddit", "evidence": "patient_reported", "ref": x["url"]}
                cur = m["treatments"].setdefault(key, [])
                if sum(1 for e in cur if e["evidence"] == "patient_reported") < 5 and ev not in cur:
                    cur.append(ev)

    # doctors patients name that no list has, for manual review
    counts, examples = collections.Counter(), {}
    for d, text in folded:
        for hit in re.finditer(r"\b(?:Dr\.?|Doctor)\s+([A-Z][a-zA-Z'\-]{2,}(?:\s+[A-Z][a-zA-Z'\-]{2,})?)", text):
            nm = hit.group(1).strip()
            if hit.group(0).lower() in matched_spans.get(d["id"], set()):
                continue
            if nm.split()[0].lower() in STOP_SURNAMES:
                continue
            counts[nm] += 1
            examples.setdefault(nm, []).append({"url": d["url"], "snippet": _snippet(d["text"], hit.start(), hit.end())})
    known = {strip_accents(m["name"]).split()[-1].lower() for m in listings if m["kind"] == "clinician"}
    known |= {v for k in known for v in _variants(k, titled)}
    unmatched = [{"name": n, "count": c, "examples": examples[n][:4]} for n, c in counts.most_common()
                 if c >= 2 and n.split()[-1].lower() not in known]
    json.dump(unmatched, open(os.path.join(os.path.dirname(CACHE), "build", "reddit_unmatched.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"reddit: {total} listings mentioned; {len(unmatched)} unmatched doctor names (>=2 mentions) for review")
