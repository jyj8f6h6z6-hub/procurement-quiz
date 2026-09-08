import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT.parents[1] / "upload"
QUESTIONS = ROOT / "data" / "questions.js"
KNOWLEDGE = ROOT / "data" / "knowledge.js"

VERSION = "3.6.3"
COMPENDIUM_NAME = "行政院公共工程委員會《政府採購法令彙編第35版》"
COMPENDIUM_URL = "https://www.pcc.gov.tw/content/index?eid=9936&type=C&lang=1"


LAW_RANGES = [
    ("政府採購法及其施行細則之條文對照", 5, 56),
    ("機關以自然人為對象之不適用政府採購法情形", 61, 62),
    ("工程價格資料庫作業辦法", 63, 64),
    ("機關採購工作及審查小組設置及作業辦法", 65, 66),
    ("查核金額", 67, 68),
    ("中央機關未達公告金額採購監辦辦法", 69, 70),
    ("公告金額", 71, 72),
    ("機關主會計及有關單位會同監辦採購辦法", 73, 76),
    ("水管、電氣與建築工程合併或分開招標原則", 77, 78),
    ("外國廠商參與非條約協定採購處理辦法", 79, 80),
    ("機關辦理涉及國家安全採購之廠商資格限制條件及審查作業辦法", 81, 84),
    ("選擇性招標錯誤行為態樣", 85, 88),
    ("政府採購法第二十二條第一項各款執行錯誤態樣", 89, 94),
    ("政府採購法第二十二條第一項第四款原有採購之適用範圍", 95, 96),
    ("機關委託專業服務廠商評選及計費辦法", 97, 102),
    ("機關委託技術服務廠商評選及計費辦法", 103, 128),
    ("機關委託資訊服務廠商評選及計費辦法", 129, 138),
    ("機關辦理設計競賽廠商評選及計費辦法", 139, 142),
    ("機關指定地區採購房地產作業辦法", 143, 150),
    ("機關委託研究發展作業辦法", 151, 152),
    ("機關邀請或委託文化藝術專業人士機構團體提供藝文服務作業辦法", 153, 156),
    ("機關委託社會福利服務廠商評選及計費辦法", 157, 162),
    ("中央機關未達公告金額採購招標辦法", 163, 164),
    ("機關辦理公告金額十分之一以下採購常見誤解或錯誤態樣", 165, 166),
    ("統包實施辦法", 167, 168),
    ("統包作業須知", 169, 170),
    ("共同投標辦法", 171, 174),
    ("政府採購法第二十六條執行注意事項", 175, 178),
    ("政府採購公告及公報發行辦法", 179, 188),
    ("機關傳輸政府採購資訊錯誤行為態樣", 189, 190),
    ("招標期限標準", 191, 194),
    ("押標金保證金暨其他擔保作業辦法", 195, 234),
    ("預付款保證金保證保險及保固保證金保證保險之保險單格式", 235, 242),
    ("依政府採購法第31條第2項第7款認定情形", 243, 244),
    ("依政府採購法第31條第2項辦理不發還或追繳押標金之執行程序", 245, 248),
    ("公共工程招標文件公開閱覽制度實施要點", 249, 252),
    ("替代方案實施辦法", 253, 256),
    ("投標廠商資格與特殊或巨額採購認定標準", 257, 262),
    ("投標廠商資格與特殊或巨額採購認定標準第4條第1項第6款認定情形", 263, 263),
    ("認定專案管理勞務採購為特殊採購", 264, 264),
    ("機關洽請代辦工程採購執行要點", 265, 268),
    ("國內廠商標價優惠實施辦法", 269, 272),
    ("中央機關小額採購", 275, 276),
    ("發現足以影響採購公正之違法或不當行為者或其他影響採購公正之違反法令行為", 277, 278),
    ("不同投標廠商間之投標文件內容有重大異常關聯之處理", 279, 280),
    ("評分及格最低標錯誤行為態樣", 281, 282),
    ("最有利標評選辦法", 283, 290),
    ("最有利標錯誤行為態樣", 291, 298),
    ("依政府採購法第五十八條處理總標價低於底價百分之八十案件之執行程序", 299, 304),
    ("依政府採購法施行細則第八十四條第一項第四款認定特殊情形", 305, 306),
    ("採購契約要項", 309, 330),
    ("工程施工查核小組組織準則", 331, 334),
    ("工程施工查核小組作業辦法", 335, 340),
    ("公共工程施工品質管理作業要點", 341, 358),
    ("採購申訴審議收費辦法", 363, 364),
    ("採購申訴審議規則", 365, 370),
    ("採購履約爭議調解規則", 371, 376),
    ("採購履約爭議調解收費辦法", 377, 380),
    ("採購申訴審議委員會組織準則", 381, 384),
    ("共同供應契約實施辦法", 389, 392),
    ("中央機關共同供應契約集中採購實施要點", 393, 396),
    ("電子採購作業辦法", 397, 402),
    ("採購評選委員會組織準則", 403, 406),
    ("採購評選委員會審議規則", 407, 412),
    ("採購評選委員會委員須知", 413, 416),
    ("各機關採購評選委員會專家學者參考名單資料庫審議小組設置要點", 417, 418),
    ("各機關採購評選委員會專家學者參考名單資料庫建置及除名作業要點", 419, 424),
    ("採購專業人員資格考試訓練發證及管理辦法", 425, 432),
    ("採購專業人員訓練計畫", 433, 446),
    ("機關優先採購環境保護產品辦法", 447, 452),
    ("扶助中小企業參與政府採購辦法", 453, 454),
    ("政府採購法第九十八條得標廠商繳納代金之方式", 455, 456),
    ("甄選投資廠商之延長履約期限程序不適用政府採購法", 457, 458),
    ("機關堪用財物無償讓與辦法", 459, 460),
    ("政府採購法第101條執行注意事項", 461, 468),
    ("特殊軍事採購適用範圍及處理辦法", 469, 472),
    ("特別採購招標決標處理辦法", 473, 476),
    ("採購文件保存之場所", 477, 478),
    ("採購稽核小組組織準則", 479, 482),
    ("採購稽核小組作業規則", 483, 488),
    ("機關提報巨額採購使用情形及效益分析作業規定", 489, 492),
    ("行政院公共工程委員會重大採購事件效益評估作業要點", 493, 494),
    ("採購人員倫理準則", 495, 498),
    ("政府採購法施行細則", 499, 530),
    ("機關辦理工程保險採購注意事項", 533, 536),
    ("政府採購法規定須報上級機關核准核定同意備查事項上級機關權責一覽表", 537, 538),
    ("機關辦理採購之廠商家數規定一覽表", 539, 540),
    ("採購契約變更或加減價核准監辦備查規定一覽表", 541, 542),
    ("變更設計之新增工程項目單價編列方式", 543, 544),
]


def load_assignment(path, prefix):
    raw = path.read_text(encoding="utf-8").strip()
    return json.loads(raw[len(prefix):].rstrip(";"))


def compact(value):
    return re.sub(r"[\s\u3000，。；：、（）()「」『』【】\[\]〈〉《》｜|／/！？?!．…—–－-]", "", value or "")


def clean_page(value):
    lines = []
    for line in value.replace("\x07", "").splitlines():
        if re.fullmatch(r"\s*總\s*\d+\s*", line):
            continue
        line = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def chinese_number(value):
    if value.isdigit():
        return int(value)
    digits = {"零": 0, "〇": 0, "○": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
    total = 0
    current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char == "十":
            total += (current or 1) * 10
            current = 0
        elif char == "百":
            total += (current or 1) * 100
            current = 0
    return total + current


def canonical_article(value):
    m = re.search(r"第\s*([一二三四五六七八九十百零〇○0-9]+)(?:\s*之\s*([一二三四五六七八九十百零〇○0-9]+))?\s*條", value or "")
    if not m:
        return ""
    main = chinese_number(m.group(1))
    sub = chinese_number(m.group(2)) if m.group(2) else None
    return f"第{main}" + (f"之{sub}" if sub is not None else "") + "條"


def pdf_text(path):
    result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True)
    return result.stdout.decode("utf-8", errors="replace").split("\f")


def load_pages():
    specs = [
        ("_01", 4), ("_02", 24), ("_03", 44), ("_04", 64), ("_05", 84),
        ("_06", 95), ("_07", 195), ("_08", 295), ("_09", 395),
        ("_10", 495), ("_11", 595),
    ]
    pages = {}
    for token, first_total in specs:
        matches = sorted(UPLOAD.glob(f"*{token}*.pdf"))
        if not matches:
            raise FileNotFoundError(token)
        chunks = pdf_text(matches[0])
        if chunks and not chunks[-1].strip():
            chunks.pop()
        for index, text in enumerate(chunks):
            total_page = first_total + index
            if total_page <= 676:
                pages[total_page] = clean_page(text)
    missing = [p for p in range(4, 677) if p not in pages]
    if missing:
        raise RuntimeError(f"missing compendium pages: {missing[:20]}")
    ocr_path = ROOT / "data" / "compendium-ocr-pages.json"
    if ocr_path.exists():
        ocr_pages = json.loads(ocr_path.read_text(encoding="utf-8")).get("pages", {})
        for page, text in ocr_pages.items():
            number = int(page)
            if len(compact(text)) > len(compact(pages.get(number, ""))):
                pages[number] = clean_page(text)
    return pages


ARTICLE_RE = re.compile(
    r"(?m)(?=^\s*(?:細則\s*)?第\s*[一二三四五六七八九十百零〇○0-9]+(?:\s*之\s*[一二三四五六七八九十百零〇○0-9]+)?\s*條)"
)


def heading_of(text):
    m = re.search(r"^\s*(?:細則\s*)?第\s*[一二三四五六七八九十百零〇○0-9]+(?:\s*之\s*[一二三四五六七八九十百零〇○0-9]+)?\s*條", text)
    if not m:
        return "相關規定"
    prefix = "施行細則 " if "細則" in m.group(0) else ""
    return prefix + canonical_article(m.group(0))


def official_articles():
    path = ROOT / "data" / "official-articles.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for source in raw.get("sources", []):
        for name in source.get("lawNames", []):
            key = norm_law_name(name)
            if key:
                result.setdefault(key, {}).update(source.get("articles", {}))
    return result


def exact_law_for_unit(unit):
    # 重用已建索引時，displayLaw 已保存條文對照表中「本法／施行細則」的辨識結果。
    # 必須優先沿用，避免標準化後的 heading 不再含「施行細則」而被反向誤判成母法。
    if unit.get("displayLaw"):
        return unit["displayLaw"]
    if unit["law"] == "政府採購法及其施行細則之條文對照":
        return "政府採購法施行細則" if unit["heading"].startswith("施行細則") else "政府採購法"
    return unit["law"]


def clean_ocr_errors(text):
    replacements = {
        "探購": "採購", "瓣法": "辦法", "辨法": "辦法", "规定": "規定", "前项": "前項",
        "第一项": "第一項", "第二项": "第二項", "第三项": "第三項", "亚應": "並應", "亚": "並",
        "换貨": "換貨", "瓣理": "辦理", "决標": "決標", "標价": "標價", "評选": "評選",
        "金额": "金額", "减價": "減價", "检附": "檢附", "證明影本": "證明影本",
        "産品": "產品", "项目": "項目", "效能經": "效能經", "追價價差": "追償價差",
        "六丶": "六、", "一丶": "一、", "二丶": "二、", "四丶": "四、", "五丶": "五、",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def build_units(pages):
    units = []
    for law_name, start, end in LAW_RANGES:
        marked = []
        cursor = 0
        page_spans = []
        for page in range(start, end + 1):
            text = pages.get(page, "")
            marked.append(text)
            page_spans.append((cursor, cursor + len(text), page))
            cursor += len(text) + 1
        joined = "\n".join(marked)
        starts = [m.start() for m in ARTICLE_RE.finditer(joined)]
        if not starts:
            # 作業規定、函文與表格以頁為完整引用單位。
            for page in range(start, end + 1):
                text = pages.get(page, "")
                if len(compact(text)) >= 35:
                    units.append({"law": law_name, "heading": "相關規定", "text": text, "pages": [page]})
            continue
        if starts[0] > 120 and len(compact(joined[:starts[0]])) >= 60:
            starts.insert(0, 0)
        starts.append(len(joined))
        for a, b in zip(starts, starts[1:]):
            text = joined[a:b].strip()
            if len(compact(text)) < 25:
                continue
            unit_pages = sorted({page for left, right, page in page_spans if left < b and right > a})
            if not unit_pages:
                unit_pages = [start]
            units.append({"law": law_name, "heading": heading_of(text), "text": text, "pages": unit_pages})
    return units


def norm_law_name(value):
    value = value or ""
    value = re.sub(r"第\s*\d+(?:\s*之\s*\d+)?\s*條.*$", "", value)
    value = re.sub(r"[｜|].*$", "", value)
    value = value.replace("政府採購招標文件公開閱覽制度實施要點", "公共工程招標文件公開閱覽制度實施要點")
    if value.strip() == "政府採購法":
        return "政府採購法及其施行細則之條文對照"
    return compact(value)


def candidate_indices(annotation, unit_laws):
    hints = []
    ref = annotation.get("legalReference") or {}
    if ref.get("lawName"):
        hints.append(ref["lawName"])
    for card in annotation.get("laws", []):
        if card.get("status") != "source-benchmark":
            hints.append(card.get("title", ""))
    norm_hints = [norm_law_name(x) for x in hints if norm_law_name(x)]
    hits = []
    for index, law in enumerate(unit_laws):
        nlaw = norm_law_name(law)
        if any(h in nlaw or nlaw in h for h in norm_hints if len(h) >= 4):
            hits.append(index)
    return hits


def query_text(question, annotation):
    parts = [question.get("question", ""), annotation.get("quickNote", "")]
    options = question.get("options") or []
    answer = question.get("answer")
    if isinstance(answer, int) and 1 <= answer <= len(options):
        parts.append(options[answer - 1])
    parts.extend(options)
    for note in annotation.get("notes", []):
        if "題庫答案" in note.get("title", "") or "答案定位" in note.get("title", ""):
            parts.append(note.get("text", ""))
    return " ".join(parts)


def best_highlights(question, law_text):
    answer_text = ""
    options = question.get("options") or []
    answer = question.get("answer")
    if isinstance(answer, int) and 1 <= answer <= len(options):
        answer_text = options[answer - 1]
    source = compact(question.get("question", "") + answer_text)
    target = compact(law_text)
    found = []
    for size in range(min(30, len(source)), 5, -1):
        for start in range(len(source) - size + 1):
            phrase = source[start:start + size]
            if phrase in target and not any(phrase in old or old in phrase for old in found):
                found.append(phrase)
                if len(found) == 3:
                    return found
    return found


def interpretation_text(card):
    title = card.get("title", "")
    if "10000325800" in title:
        return (
            "工程企字第10000325800號函｜說明二：\n"
            "配合本會100年7月11日發布之「工程價格資料庫作業辦法」自101年1月1日施行，機關辦理資訊服務採購之決標亦自101年1月1日起，須傳輸得標廠商之資訊服務價格資料。\n"
            "（一）標的分類選取「84電腦及相關服務」，且預算金額達1,000萬元以上之適用及準用最有利標案件，於傳輸決標公告時，必須一併登載得標廠商「人員職稱」及「每月實際薪資」。該分類其餘案件，由機關自行決定是否登載。"
        )
    if "10100137940" in title:
        return (
            "工程企字第10100137940號函｜說明二、三：\n"
            "二、關於採購評選委員會外聘委員之「聘兼」程序，政府採購法規尚無明文規定須出具聘書（函）。機關出具之相關文書如有明示、默示或經解釋為有聘兼之意思表示，即可認定為已完成「聘兼」程序。\n"
            "三、專家學者建議名單簽請機關首長或其授權人員勾選後，發出外聘委員意願調查表，並將意願調查結果連同開會通知單簽報核定；嗣後以機關名義發出的開會通知單載有遴聘專家學者姓名，即可認定已完成「聘兼」程序，無需另出具聘書（函）。"
        )
    return ""


def explicit_article(annotation, question):
    values = [question.get("legalBasis", ""), (annotation.get("legalReference") or {}).get("article", "")]
    values.extend(card.get("title", "") for card in annotation.get("laws", []))
    for value in values:
        article = canonical_article(value)
        if article:
            return article
    question_text = question.get("question", "")
    ref_law = (annotation.get("legalReference") or {}).get("lawName", "")
    aliases = [ref_law]
    if ref_law == "政府採購法":
        aliases.extend(["政府採購法", "採購法"])
    elif ref_law == "政府採購法施行細則":
        aliases.extend(["政府採購法施行細則", "採購法施行細則", "施行細則"])
    if ref_law and any(alias and compact(alias) in compact(question_text) for alias in aliases):
        article = canonical_article(question_text)
        if article:
            return article
    return ""


def main():
    questions = load_assignment(QUESTIONS, "window.QUESTION_BANK = ")
    knowledge = load_assignment(KNOWLEDGE, "window.KNOWLEDGE = ")
    existing_index = ROOT / "data" / "compendium-index.json"
    if "--reuse-index" in sys.argv and existing_index.exists():
        units = json.loads(existing_index.read_text(encoding="utf-8"))["units"]
        indexed_page_count = int(knowledge.get("coverage", {}).get("compendiumIndexedPages", 674))
    else:
        pages = load_pages()
        units = build_units(pages)
        indexed_page_count = len(pages)
    official = official_articles()
    corrected_units = []
    for unit in units:
        law_name = exact_law_for_unit(unit)
        article_name = canonical_article(unit["heading"])
        exact = official.get(norm_law_name(law_name), {})
        if article_name and exact:
            if article_name not in exact:
                # OCR 將內文中的交互引用誤當成新條號；不建立錯誤法條卡。
                continue
            unit["text"] = article_name + "\n" + exact[article_name]
            unit["heading"] = article_name
            unit["displayLaw"] = law_name
            unit["textVerifiedByOfficial"] = True
        else:
            unit["text"] = clean_ocr_errors(unit["text"])
            unit["displayLaw"] = law_name
            unit["textVerifiedByOfficial"] = False
        corrected_units.append(unit)
    units = corrected_units
    unit_texts = [compact(u["law"] + u["heading"] + u["text"]) for u in units]
    unit_laws = [u["law"] for u in units]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1, sublinear_tf=True)
    unit_matrix = vectorizer.fit_transform(unit_texts)
    q_by_id = {q["id"]: q for q in questions}

    matched = 0
    strong = 0
    weak = 0
    outside = 0
    reports = []
    query_cache = {}
    stale_hint_overrides = 0
    for qid, annotation in knowledge["annotations"].items():
        q = q_by_id[qid]
        query = compact(query_text(q, annotation))
        query_cache[qid] = query
        qvec = vectorizer.transform([query])
        restricted = candidate_indices(annotation, unit_laws)
        pool = restricted or list(range(len(units)))
        article = explicit_article(annotation, q)
        if article:
            exact_pool = [idx for idx in pool if canonical_article(units[idx].get("heading", "")) == article]
            ref_law = (annotation.get("legalReference") or {}).get("lawName", "")
            if ref_law:
                law_exact_pool = [idx for idx in exact_pool if norm_law_name(units[idx].get("displayLaw", exact_law_for_unit(units[idx]))) == norm_law_name(ref_law)]
                if law_exact_pool:
                    exact_pool = law_exact_pool
            if exact_pool:
                earliest = min(min(units[idx]["pages"]) for idx in exact_pool)
                pool = [idx for idx in exact_pool if min(units[idx]["pages"]) == earliest]

        # 舊題庫的 lawName 有時本身就是錯置資料。若題目沒有明示條號，且受限候選
        # 幾乎完全不相關，允許由全彙編中顯著較高的逐字／近逐字命中覆寫舊標籤。
        # 門檻刻意保守：全域分數至少 0.30、受限分數低於 0.08，且差距至少 0.20。
        overrode_stale_hint = False
        if restricted and not article:
            restricted_scores = cosine_similarity(qvec, unit_matrix[restricted]).ravel()
            restricted_best = float(np.max(restricted_scores)) if len(restricted_scores) else 0.0
            global_scores = cosine_similarity(qvec, unit_matrix).ravel()
            global_best = float(np.max(global_scores)) if len(global_scores) else 0.0
            if restricted_best < 0.08 and global_best >= 0.30 and global_best - restricted_best >= 0.20:
                pool = list(range(len(units)))
                overrode_stale_hint = True
                stale_hint_overrides += 1

        # 彙編後段可能再次引述同一條文。同法規、同條號、同內容只保留總頁碼最前者，
        # 使法規本體頁優先於後段教材、流程或附錄中的重複引文。
        earliest_by_content = {}
        for idx in pool:
            unit = units[idx]
            key = (
                norm_law_name(unit.get("displayLaw", unit["law"])),
                canonical_article(unit.get("heading", "")) or compact(unit.get("heading", "")),
                compact(unit.get("text", "")),
            )
            previous = earliest_by_content.get(key)
            if previous is None or min(unit["pages"]) < min(units[previous]["pages"]):
                earliest_by_content[key] = idx
        pool = list(earliest_by_content.values())
        scores = cosine_similarity(qvec, unit_matrix[pool]).ravel()
        order = np.argsort(scores)[::-1]
        chosen = []
        chosen_keys = set()
        for rank in order[:12]:
            idx = pool[int(rank)]
            score = float(scores[int(rank)])
            unit = units[idx]
            if article and article.replace(" ", "") == unit["heading"].replace(" ", ""):
                score += 0.32
            if chosen and score < max(0.12, chosen[0][0] * 0.62):
                continue
            if len(unit["text"]) > 3800:
                continue
            key = (unit.get("displayLaw", unit["law"]), unit["heading"], compact(unit["text"]))
            if key in chosen_keys:
                continue
            chosen_keys.add(key)
            chosen.append((score, unit))
            if len(chosen) >= (2 if score >= 0.18 else 1):
                break

        # 已由彙編逐條人工確認的題目，以答案所考的直接規範取代舊題庫錯置法源。
        if qid == "q0034":
            requested = [
                ("機關委託技術服務廠商評選及計費辦法", "第1條"),
                ("機關委託技術服務廠商評選及計費辦法", "第39條"),
            ]
            manual = []
            for law_name, heading in requested:
                candidates = [
                    unit for unit in units
                    if unit.get("displayLaw", exact_law_for_unit(unit)) == law_name
                    and canonical_article(unit.get("heading", "")) == heading
                ]
                if candidates:
                    unit = min(candidates, key=lambda item: min(item["pages"]))
                    manual.append((1.0, unit))
            if len(manual) == len(requested):
                chosen = manual
                if not overrode_stale_hint:
                    stale_hint_overrides += 1
                overrode_stale_hint = True
        elif qid == "q0036":
            requested = [
                ("押標金保證金暨其他擔保作業辦法", "第15條"),
                ("押標金保證金暨其他擔保作業辦法", "第18條"),
                ("押標金保證金暨其他擔保作業辦法", "第19條"),
            ]
            manual = []
            for law_name, heading in requested:
                candidates = [
                    unit for unit in units
                    if unit.get("displayLaw", exact_law_for_unit(unit)) == law_name
                    and canonical_article(unit.get("heading", "")) == heading
                ]
                if candidates:
                    unit = min(candidates, key=lambda item: min(item["pages"]))
                    manual.append((1.0, unit))
            if len(manual) == len(requested):
                chosen = manual
                if not overrode_stale_hint:
                    stale_hint_overrides += 1
                overrode_stale_hint = True

        old_laws = annotation.get("laws", [])
        external_cards = []
        for card in old_laws:
            if card.get("status") == "source-benchmark":
                continue
            title_norm = norm_law_name(card.get("title", ""))
            covered = any(title_norm and (title_norm in norm_law_name(u[1]["law"]) or norm_law_name(u[1]["law"]) in title_norm) for u in chosen)
            compendium_text_verified = any(u[1].get("textVerifiedByOfficial") for u in chosen)
            direct_text = card.get("lawText") or interpretation_text(card)
            is_interpretation = "函" in card.get("sourceType", "") or "函" in card.get("title", "")
            if direct_text and (is_interpretation or not covered or not compendium_text_verified):
                card["lawText"] = direct_text
                card["inlineOnly"] = True
                card["sourcePriority"] = "official-supplement"
                external_cards.append(card)
        if qid in {"q0034", "q0036"}:
            external_cards = []

        new_cards = []
        for score, unit in chosen:
            page_text = "、".join(str(p) for p in unit["pages"])
            title = unit.get("displayLaw", unit["law"])
            if unit["heading"] != "相關規定":
                title += " " + unit["heading"]
            card = {
                "title": title,
                "sourceType": "政府採購法令彙編第35版",
                "sourceLabel": "行政院公共工程委員會",
                "sourcePriority": "compendium-primary",
                "compendiumPage": page_text,
                "lawText": unit["text"],
                "highlights": best_highlights(q, unit["text"]),
                "text": f"本題相關規範收錄於《政府採購法令彙編第35版》總{page_text}頁。",
                "url": COMPENDIUM_URL,
                "inlineOnly": True,
                "status": "compendium-embedded",
                "matchConfidence": round(score, 4),
                "textVerifiedByOfficial": bool(unit.get("textVerifiedByOfficial")),
            }
            new_cards.append(card)
        annotation["laws"] = new_cards + external_cards
        if new_cards:
            matched += 1
            if chosen[0][0] >= 0.18 or article:
                strong += 1
            else:
                weak += 1
        else:
            outside += 1
        annotation["lawStatus"] = "compendium-located" if (new_cards and (article or chosen[0][0] >= 0.18)) else ("compendium-review" if new_cards else "official-supplement")
        annotation["compendiumMatchConfidence"] = round(chosen[0][0], 4) if chosen else 0
        if qid == "q0034":
            annotation["quickNote"] = "適用與準用｜D｜依採購法第22條第1項第9款辦理者適用本辦法；非依該款辦理者，才是得準用。"
            annotation["notes"] = [
                {
                    "title": "答案定位",
                    "text": "本題答案為D。題幹已明示依政府採購法第22條第1項第9款辦理，因此不是『準用』《機關委託技術服務廠商評選及計費辦法》。",
                },
                {
                    "title": "適用與準用",
                    "text": "本辦法第39條以反面方式劃分：非依採購法第22條第1項第9款辦理者，才『得準用』本辦法；依該款辦理的技術服務採購則屬本辦法直接規範的案件。",
                },
                {
                    "title": "彙編出處",
                    "text": "《機關委託技術服務廠商評選及計費辦法》第1條收錄於彙編總103頁；第39條收錄於總122頁。",
                },
            ]
            annotation["optionExplanations"] = [
                {"label": "A", "text": "不是本題錯誤選項。"},
                {"label": "B", "text": "不是本題錯誤選項。"},
                {"label": "C", "text": "不是本題錯誤選項。"},
                {"label": "D", "text": "錯誤。依本辦法第39條，非依採購法第22條第1項第9款辦理者才得準用；本題正是依該款辦理，不能稱為準用。"},
            ]
            annotation["legalReference"] = {
                "lawName": "機關委託技術服務廠商評選及計費辦法",
                "article": "第1條、第39條",
                "url": "https://lawweb.pcc.gov.tw/LawContent.aspx?id=FL000676",
            }
            for card in annotation.get("laws", []):
                if card.get("title", "").endswith("第39條"):
                    card["highlights"] = [
                        "非依本法第二十二條第一項第九款辦理者",
                        "得準用本辦法之規定",
                    ]
        elif qid == "q0036":
            annotation["quickNote"] = "逐選項法規對照｜D｜5%並非法定固定比率，而是第15條容許機關於不逾10%的原則內擇定。"
            annotation["notes"] = [
                {
                    "title": "答案定位",
                    "text": "本題答案為D。第15條准許機關在招標文件中擇定履約保證金的一定比率，原則上不逾契約金額10%；5%在容許範圍內，但不是所有採購一律法定5%。",
                },
                {
                    "title": "錯誤選項也要有依據",
                    "text": "A應對照第18條、B應對照第19條；C經本辦法查核，並無一律要求廠商必須提出連帶保證廠商的規定。不能只列正確答案D的第15條。",
                },
            ]
            annotation["optionReviews"] = [
                {
                    "label": "A", "verdict": "錯誤", "article": "押標金保證金暨其他擔保作業辦法第18條", "compendiumPage": "200",
                    "text": "第18條規定繳納期限由機關依案件性質及實際需要合理訂定；查核金額以上採購應訂14日以上合理期限，並非一律得標後10天。",
                },
                {
                    "label": "B", "verdict": "錯誤", "article": "押標金保證金暨其他擔保作業辦法第19條", "compendiumPage": "200",
                    "text": "第19條規定得依履約進度、驗收、維修或保固等條件一次或分次發還，由機關在招標文件訂明；並非強制分2期平均發還。",
                },
                {
                    "label": "C", "verdict": "錯誤", "article": "法規查核結論", "compendiumPage": "",
                    "text": "本辦法沒有規定廠商辦理本案時必須提出連帶保證廠商；不能把可採行的擔保安排寫成一律必須具備的條件。",
                },
                {
                    "label": "D", "verdict": "正確", "article": "押標金保證金暨其他擔保作業辦法第15條", "compendiumPage": "199",
                    "text": "第15條允許機關在招標文件中擇定一定比率，原則上不逾契約金額10%；5%屬可擇定範圍，但不是法定固定比率。",
                },
            ]
            annotation["optionExplanations"] = [
                {"label": row["label"], "text": row["verdict"] + "。" + row["text"]}
                for row in annotation["optionReviews"]
            ]
            annotation["legalReference"] = {
                "lawName": "押標金保證金暨其他擔保作業辦法",
                "article": "第15條、第18條、第19條",
                "url": "https://lawweb.pcc.gov.tw/",
            }
            option_map = {"第15條": ["D"], "第18條": ["A"], "第19條": ["B"]}
            highlight_map = {
                "第15條": ["一定比率，以不逾契約金額之百分之十為原則"],
                "第18條": ["由機關視案件性質及實際需要，於招標文件中合理訂定之", "應訂定十四日以上之合理期限"],
                "第19條": ["一次或分次發還", "由機關視案件性質及實際需要，於招標文件中訂明"],
            }
            for card in annotation.get("laws", []):
                article = canonical_article(card.get("title", ""))
                card["relatedOptions"] = option_map.get(article, [])
                card["highlights"] = highlight_map.get(article, card.get("highlights", []))
        reports.append({
            "questionId": qid,
            "articleHint": article,
            "restrictedByLawName": bool(restricted),
            "overrodeStaleLawHint": overrode_stale_hint,
            "topScore": round(chosen[0][0], 4) if chosen else 0,
            "cards": [{"title": c[1]["law"] + " " + c[1]["heading"], "pages": c[1]["pages"]} for c in chosen],
            "externalCards": len(external_cards),
        })

    # 同一課程題庫含大量重複／改寫題。對無明示條號且低分者，只在同一類別中，
    # 以高度相似（>=0.80）的已定位題繼承法規卡，避免跨章節猜測。
    report_by_id = {row["questionId"]: row for row in reports}
    seed_ids = [row["questionId"] for row in reports if row["articleHint"] or row["topScore"] >= 0.18]
    weak_ids = [row["questionId"] for row in reports if not row["articleHint"] and row["topScore"] < 0.18]
    category_seeds = {}
    for qid in seed_ids:
        category_seeds.setdefault(q_by_id[qid]["category"], []).append(qid)
    propagated = 0
    for qid in weak_ids:
        seeds = category_seeds.get(q_by_id[qid]["category"], [])
        if not seeds:
            continue
        sims = cosine_similarity(vectorizer.transform([query_cache[qid]]), vectorizer.transform([query_cache[x] for x in seeds])).ravel()
        best_pos = int(np.argmax(sims))
        similarity = float(sims[best_pos])
        if similarity < 0.80:
            continue
        source_id = seeds[best_pos]
        copied = []
        for card in knowledge["annotations"][source_id].get("laws", []):
            if card.get("sourcePriority") != "compendium-primary":
                continue
            cloned = json.loads(json.dumps(card, ensure_ascii=False))
            cloned["highlights"] = best_highlights(q_by_id[qid], cloned.get("lawText", ""))
            cloned["inheritedFromRelatedQuestion"] = source_id
            copied.append(cloned)
        if not copied:
            continue
        supplements = [c for c in knowledge["annotations"][qid].get("laws", []) if c.get("sourcePriority") == "official-supplement"]
        knowledge["annotations"][qid]["laws"] = copied + supplements
        knowledge["annotations"][qid]["lawStatus"] = "compendium-located-related-question"
        report_by_id[qid]["propagatedFrom"] = source_id
        report_by_id[qid]["questionSimilarity"] = round(similarity, 4)
        propagated += 1
    strong += propagated
    weak -= propagated

    knowledge["version"] = VERSION
    knowledge["calibration"] = {
        "baseline": COMPENDIUM_NAME,
        "compendiumUrl": COMPENDIUM_URL,
        "pageRange": "總3至總676頁",
        "principle": "第35版彙編為第一順位；彙編未收錄時，始以全國法規資料庫、工程會函釋查詢及工程會網站補充，且原文直接內嵌。",
        "calibratedAt": "2026-09-08",
    }
    knowledge["sources"]["priority"] = [
        {"name": "政府採購法令彙編第35版", "url": COMPENDIUM_URL, "role": "第一順位；顯示原文及總頁碼"},
        {"name": "全國法規資料庫", "url": "https://law.moj.gov.tw/Index.aspx", "role": "彙編未收錄時補充"},
        {"name": "政府採購法規解釋函令及相關函文查詢", "url": "https://planpe.pcc.gov.tw/prms/explainLetter/readPrmsExplainLetterSearch", "role": "彙編未收錄時補充"},
        {"name": "行政院公共工程委員會", "url": "https://www.pcc.gov.tw/", "role": "彙編未收錄時補充"},
    ]
    coverage = knowledge.setdefault("coverage", {})
    final_cards = [card for annotation in knowledge["annotations"].values() for card in annotation.get("laws", [])]
    coverage.update({
        "totalQuestions": len(questions),
        "lawCards": len(final_cards),
        "compendiumIndexedPages": indexed_page_count,
        "compendiumUnits": len(units),
        "questionsWithCompendiumText": matched,
        "strongCompendiumMatches": strong,
        "weakCompendiumMatchesForReview": weak,
        "highSimilarityMappings": propagated,
        "staleLawHintOverrides": stale_hint_overrides,
        "questionsWithoutCompendiumMatch": outside,
        "genericBenchmarkCardsRemaining": sum(1 for a in knowledge["annotations"].values() for c in a.get("laws", []) if c.get("status") == "source-benchmark"),
        "allDisplayedCardsContainDirectText": all(c.get("lawText") for a in knowledge["annotations"].values() for c in a.get("laws", [])),
        "compendiumPagesDisplayed": True,
        "compendiumCards": sum(1 for card in final_cards if card.get("compendiumPage")),
        "officialSupplementCards": sum(1 for card in final_cards if card.get("sourcePriority") == "official-supplement"),
        "emptyLawCards": sum(1 for card in final_cards if not card.get("lawText")),
    })
    KNOWLEDGE.write_text("window.KNOWLEDGE = " + json.dumps(knowledge, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    (ROOT / "data" / "compendium-index.json").write_text(json.dumps({"version": VERSION, "name": COMPENDIUM_NAME, "units": units}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "data" / "compendium-matching-report.json").write_text(json.dumps({
        "version": VERSION,
        "totalQuestions": len(questions),
        "matched": matched,
        "strong": strong,
        "weakReview": weak,
        "highSimilarityMappings": propagated,
        "staleLawHintOverrides": stale_hint_overrides,
        "unmatched": outside,
        "questions": reports,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pages": indexed_page_count, "units": len(units), "matched": matched, "strong": strong, "weak": weak, "unmatched": outside, "staleLawHintOverrides": stale_hint_overrides}, ensure_ascii=False))


if __name__ == "__main__":
    main()
