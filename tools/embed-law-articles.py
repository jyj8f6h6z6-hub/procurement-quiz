import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen
from lxml import html as lxml_html

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data" / "questions.js"
KNOWLEDGE = ROOT / "data" / "knowledge.js"
CACHE = ROOT / ".law-cache"
CACHE.mkdir(exist_ok=True)

def load_assignment(path, prefix):
    raw = path.read_text(encoding="utf-8").strip()
    return json.loads(raw[len(prefix):].rstrip(";"))

def normalized_article(value):
    m = re.search(r"第\s*(\d+(?:\s*之\s*\d+)?)\s*條", value or "")
    return "第" + re.sub(r"\s+", "", m.group(1)) + "條" if m else None

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"[ \t\u3000]+", "", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()

def fetch(url):
    cache = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url)[-150:] + ".html")
    if cache.exists():
        return cache.read_bytes()
    req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(req, timeout=15) as response:
        data = response.read()
    cache.write_bytes(data)
    time.sleep(.15)
    return data

def parse_articles(url, data):
    tree = lxml_html.fromstring(data)
    result = {}
    if "lawweb.pcc.gov.tw" in url:
        for row in tree.xpath("//tr[td]"):
            cells = row.xpath("./td")
            if len(cells) < 2:
                continue
            label = normalized_article("".join(cells[0].itertext()))
            if label:
                result[label] = clean_text("\n".join(cells[1].itertext()))
    elif "law.moj.gov.tw" in url:
        labels = tree.xpath("//div[contains(@class,'col-no')]")
        for label_node in labels:
            label = normalized_article("".join(label_node.itertext()))
            parent = label_node.getparent()
            content = parent.xpath(".//div[contains(@class,'law-article') or contains(@class,'col-data') or contains(@class,'col-data-no')]")
            if label and content:
                result[label] = clean_text("\n".join(content[0].itertext()))
    return result

def best_highlights(question, law_text):
    source = question.get("question", "")
    if question.get("type") == "choice":
        answer = question.get("answer", 0)
        options = question.get("options") or []
        if isinstance(answer, int) and 1 <= answer <= len(options):
            source += options[answer - 1]
    source = re.sub(r"[，。；：、（）()「」『』\s]", "", source)
    compact = re.sub(r"[，。；：、（）()「」『』\s]", "", law_text)
    candidates = []
    max_len = min(28, len(source))
    for size in range(max_len, 5, -1):
        for start in range(0, len(source) - size + 1):
            phrase = source[start:start+size]
            if phrase in compact and not any(phrase in x or x in phrase for x in candidates):
                candidates.append(phrase)
                if len(candidates) == 2:
                    return candidates
    return candidates

questions = load_assignment(QUESTIONS, "window.QUESTION_BANK = ")
knowledge = load_assignment(KNOWLEDGE, "window.KNOWLEDGE = ")
question_by_id = {q["id"]: q for q in questions}

targets = {}
for qid, annotation in knowledge["annotations"].items():
    for card in annotation.get("laws", []):
        article = normalized_article(card.get("title"))
        url = card.get("url", "")
        if article and not card.get("lawText") and ("lawweb.pcc.gov.tw" in url or "law.moj.gov.tw" in url):
            targets.setdefault(url, []).append((qid, card, article))

article_sets = {}
errors = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(fetch, url): url for url in targets}
    for future in as_completed(futures):
        url = futures[future]
        try:
            article_sets[url] = parse_articles(url, future.result())
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})

embedded = 0
unmatched = []
for url, cards in targets.items():
    articles = article_sets.get(url, {})
    for qid, card, article in cards:
        law_text = articles.get(article)
        if not law_text:
            unmatched.append({"questionId": qid, "article": article, "url": url})
            continue
        card["lawText"] = law_text
        highlights = best_highlights(question_by_id[qid], law_text)
        if highlights:
            card["highlights"] = highlights
        card["inlineOnly"] = True
        card["status"] = "article-embedded"
        embedded += 1

knowledge["version"] = "3.5.0"
knowledge.setdefault("sources", {})["priority"] = [
    {"name":"政府採購法令彙編第35版", "url":"https://www.pcc.gov.tw/content/index?eid=9936&type=C&lang=1", "role":"主要校正基準"},
    {"name":"工程會主管法規查詢系統", "url":"https://lawweb.pcc.gov.tw", "role":"現行條文核對與內嵌來源"},
    {"name":"工程會政府採購法規解釋函令", "url":"https://planpe.pcc.gov.tw/prms/explainLetter", "role":"解釋疑義輔助來源"},
    {"name":"使用者指定函釋60046189", "url":"https://planpe.pcc.gov.tw/prms/explainLetter/readPrmsExplainLetterContentDetail?pkPrmsRuleContent=60046189", "role":"個別題目直接依據"},
    {"name":"全國法規資料庫", "url":"https://law.moj.gov.tw/Index.aspx", "role":"工程會未收錄法規之補充來源"}
]
knowledge["coverage"]["embeddedLawArticleCards"] = sum(1 for a in knowledge["annotations"].values() for c in a.get("laws", []) if c.get("lawText"))
knowledge["coverage"]["newlyEmbeddedLawArticleCards"] = embedded
knowledge["coverage"]["externalLawButtonsHiddenWhenEmbedded"] = True

KNOWLEDGE.write_text("window.KNOWLEDGE = " + json.dumps(knowledge, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
(ROOT / "data" / "article-embedding-report.json").write_text(json.dumps({
    "version":"3.5.0", "targets":sum(len(x) for x in targets.values()), "embedded":embedded,
    "unmatched":unmatched, "fetchErrors":errors
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"urls":len(targets), "targets":sum(len(x) for x in targets.values()), "embedded":embedded, "unmatched":len(unmatched), "errors":len(errors)}, ensure_ascii=False))
sys.exit(0)
