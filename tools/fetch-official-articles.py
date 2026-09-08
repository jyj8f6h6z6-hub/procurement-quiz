import html
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from lxml import html as lxml_html


ROOT = Path(__file__).resolve().parents[1]
SOURCE_KNOWLEDGE = ROOT.parent / "procurement-quiz-v3.5.0" / "data" / "knowledge.js"
OUTPUT = ROOT / "data" / "official-articles.json"
CACHE = ROOT / ".official-cache"
CACHE.mkdir(exist_ok=True)


def load_assignment(path, prefix):
    raw = path.read_text(encoding="utf-8").strip()
    return json.loads(raw[len(prefix):].rstrip(";"))


def compact(value):
    return re.sub(r"[\s\u3000，。；：、（）()「」『』【】\[\]〈〉《》｜|／/]", "", value or "")


def clean(value):
    value = html.unescape(value or "").replace("\xa0", " ").replace("\x07", "")
    lines = [re.sub(r"[ \t\u3000]+", " ", x).strip() for x in value.splitlines()]
    return "\n".join(x for x in lines if x)


def article(value):
    m = re.search(r"第\s*(\d+(?:\s*之\s*\d+)?)\s*條", value or "")
    return "第" + re.sub(r"\s+", "", m.group(1)) + "條" if m else ""


def fetch(url):
    filename = re.sub(r"[^A-Za-z0-9]+", "_", url)[-160:] + ".html"
    path = CACHE / filename
    if path.exists():
        return path.read_bytes()
    data = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read()
    path.write_bytes(data)
    time.sleep(0.15)
    return data


def parse_lawweb(data):
    tree = lxml_html.fromstring(data)
    result = {}
    for row in tree.xpath("//tr[td]"):
        cells = row.xpath("./td")
        if len(cells) < 2:
            continue
        label = article("".join(cells[0].itertext()))
        body = clean("\n".join(cells[1].itertext()))
        if label and body:
            result[label] = body
    return result


def parse_moj(data):
    tree = lxml_html.fromstring(data)
    result = {}
    for label_node in tree.xpath("//div[contains(@class,'col-no')]"):
        label = article("".join(label_node.itertext()))
        row = label_node
        while row is not None and "row" not in (row.get("class") or "").split():
            row = row.getparent()
        if row is None:
            continue
        candidates = row.xpath(".//div[contains(@class,'law-article') or contains(@class,'col-data')]")
        body = clean("\n".join(candidates[-1].itertext())) if candidates else ""
        if label and body:
            result[label] = body
    return result


def main():
    knowledge = load_assignment(SOURCE_KNOWLEDGE, "window.KNOWLEDGE = ")
    url_names = {}
    for annotation in knowledge["annotations"].values():
        ref = annotation.get("legalReference") or {}
        if ref.get("url") and ref.get("lawName"):
            url_names.setdefault(ref["url"], set()).add(ref["lawName"])
        for card in annotation.get("laws", []):
            if card.get("url") and card.get("title"):
                name = re.sub(r"\s*第\s*\d+(?:\s*之\s*\d+)?\s*條.*$", "", card["title"])
                name = re.sub(r"[｜|].*$", "", name).strip()
                url_names.setdefault(card["url"], set()).add(name)

    # 補入彙編高頻法規的官方全文入口。
    supplements = {
        "https://lawweb.pcc.gov.tw/LawContent.aspx?id=FL000683": {"機關優先採購環境保護產品辦法"},
        "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030058": {"政府採購法施行細則"},
        "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030081": {"共同供應契約實施辦法"},
    }
    for url, names in supplements.items():
        url_names.setdefault(url, set()).update(names)

    sources = []
    errors = []
    for url, names in sorted(url_names.items()):
        if "lawweb.pcc.gov.tw/LawContent" not in url and "law.moj.gov.tw/LawClass/Law" not in url:
            continue
        try:
            data = fetch(url)
            articles = parse_lawweb(data) if "lawweb.pcc.gov.tw" in url else parse_moj(data)
            if not articles:
                raise ValueError("no articles parsed")
            sources.append({"url": url, "lawNames": sorted(names), "articles": articles})
            print(url, len(articles), flush=True)
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
    OUTPUT.write_text(json.dumps({"version": "3.6.1", "sources": sources, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(sources), "errors": len(errors), "articles": sum(len(x["articles"]) for x in sources)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
