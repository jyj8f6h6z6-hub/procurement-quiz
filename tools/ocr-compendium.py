import json
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT.parents[1] / "upload"
CACHE = ROOT / "data" / "compendium-ocr-pages.json"

SPECS = [
    ("_01", 4), ("_02", 24), ("_03", 44), ("_04", 64), ("_05", 84),
    ("_06", 95), ("_07", 195), ("_08", 295), ("_09", 395),
    ("_10", 495), ("_11", 595),
]


def extracted_pages(path):
    raw = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True).stdout
    pages = raw.decode("utf-8", errors="replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def ocr_one(job):
    total_page, pdf_path, local_page = job
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    with tempfile.TemporaryDirectory(prefix="compendium-ocr-") as folder:
        prefix = str(Path(folder) / "page")
        subprocess.run([
            "pdftoppm", "-f", str(local_page), "-l", str(local_page), "-png", "-r", "135",
            "-singlefile", str(pdf_path), prefix
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result, _ = engine(prefix + ".png")
    rows = []
    for item in result or []:
        box, text, confidence = item
        if confidence < 0.42:
            continue
        y = sum(point[1] for point in box) / 4
        x = sum(point[0] for point in box) / 4
        # 排除頁側章節標籤；保留頁尾總頁碼供後續驗證。
        if x < 120 and len(text) <= 8:
            continue
        rows.append((round(y, 1), round(x, 1), text))
    rows.sort(key=lambda row: (row[0], row[1]))
    return total_page, "\n".join(row[2] for row in rows)


def main():
    jobs = []
    for token, first_total in SPECS:
        matches = sorted(UPLOAD.glob(f"*{token}*.pdf"))
        if not matches:
            raise FileNotFoundError(token)
        pdf_path = matches[0]
        for index, text in enumerate(extracted_pages(pdf_path)):
            total_page = first_total + index
            if total_page > 676:
                continue
            length = len(re.sub(r"\s", "", text))
            if length < 120:
                jobs.append((total_page, str(pdf_path), index + 1))
    existing = {}
    if CACHE.exists():
        existing = json.loads(CACHE.read_text(encoding="utf-8")).get("pages", {})
    jobs = [job for job in jobs if str(job[0]) not in existing]
    completed = dict(existing)
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(ocr_one, job) for job in jobs]
        for number, future in enumerate(as_completed(futures), 1):
            page, text = future.result()
            completed[str(page)] = text
            if number % 20 == 0:
                CACHE.write_text(json.dumps({"version": "3.6.3", "pages": completed}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"OCR {number}/{len(jobs)}", flush=True)
    CACHE.write_text(json.dumps({"version": "3.6.3", "pages": dict(sorted(completed.items(), key=lambda x: int(x[0])))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ocrPages": len(completed), "newPages": len(jobs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
