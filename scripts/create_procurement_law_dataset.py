"""Створення датасету нормативних актів публічних закупівель України для RAG."""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


OUTPUT_PATH = Path("data/law/procurement_legal_dataset.jsonl")
REPORTS_DIR = Path("reports")

# для української cl100k токенізації ~2.3 chars/token.
# 2000 chars ≈ 700-850 токенів — комфортно для більшості ембедерів,
# при цьому залишається запас контексту і не б'ється про ліміт 512 у
# моделей типу BGE-M3 / multilingual-e5 (за рахунок легкої толерантності).
CHUNK_MAX_CHARS = 2000
CHUNK_MIN_CHARS = 700
CHUNK_OVERLAP_CHARS = 220
SECTION_MIN_CHARS = 250
REQUEST_DELAY_SECONDS = 1

DOCUMENTS: list[dict[str, Any]] = [
    {
        "doc_id": "law_922_public_procurement",
        "title": "Закон України «Про публічні закупівлі»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "public_procurement",
        "url": "https://zakon.rada.gov.ua/laws/show/922-19#Text",
    },
    {
        "doc_id": "cmu_1178_wartime_procurement",
        "title": "Постанова КМУ №1178 від 12.10.2022",
        "type": "resolution",
        "authority": "Кабінет Міністрів України",
        "domain": "public_procurement_wartime",
        "url": "https://zakon.rada.gov.ua/laws/show/1178-2022-%D0%BF#Text",
    },
    {
        "doc_id": "cmu_1275_defense_wartime_procurement",
        "title": "Постанова КМУ №1275 від 11.11.2022",
        "type": "resolution",
        "authority": "Кабінет Міністрів України",
        "domain": "defense_procurement_wartime",
        "url": "https://zakon.rada.gov.ua/laws/show/1275-2022-%D0%BF#Text",
    },
    {
        "doc_id": "cmu_166_e_procurement_system",
        "title": "Постанова КМУ №166 від 24.02.2016",
        "type": "resolution",
        "authority": "Кабінет Міністрів України",
        "domain": "prozorro_system",
        "url": "https://zakon.rada.gov.ua/laws/show/166-2016-%D0%BF#Text",
    },
    {
        "doc_id": "cmu_822_e_catalog",
        "title": "Постанова КМУ №822 від 14.09.2020",
        "type": "resolution",
        "authority": "Кабінет Міністрів України",
        "domain": "prozorro_market",
        "url": "https://zakon.rada.gov.ua/laws/show/822-2020-%D0%BF#Text",
    },
    {
        "doc_id": "mineconomy_708_subject_of_procurement",
        "title": "Наказ Мінекономіки №708 від 15.04.2020",
        "type": "order",
        "authority": "Міністерство економіки України",
        "domain": "procurement_subject",
        "url": "https://zakon.rada.gov.ua/laws/show/z0500-20#Text",
    },
    {
        "doc_id": "mineconomy_1082_publication_order",
        "title": "Наказ Мінекономіки №1082 від 11.06.2020",
        "type": "order",
        "authority": "Міністерство економіки України",
        "domain": "publication_rules",
        "url": "https://zakon.rada.gov.ua/laws/show/z0610-20#Text",
    },
    {
        "doc_id": "cmu_292_complaint_fee",
        "title": "Постанова КМУ №292 від 22.04.2020",
        "type": "resolution",
        "authority": "Кабінет Міністрів України",
        "domain": "complaints",
        "url": "https://zakon.rada.gov.ua/laws/show/292-2020-%D0%BF#Text",
    },
    {
        "doc_id": "law_808_defense_procurement",
        "title": "Закон України «Про оборонні закупівлі»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "defense_procurement",
        "url": "https://zakon.rada.gov.ua/laws/show/808-20#Text",
    },
    {
        "doc_id": "law_851_e_documents",
        "title": "Закон України «Про електронні документи та електронний документообіг»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "electronic_documents",
        "url": "https://zakon.rada.gov.ua/laws/show/851-15#Text",
    },
    {
        "doc_id": "law_2155_e_identification_trust_services",
        "title": "Закон України «Про електронну ідентифікацію та електронні довірчі послуги»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "electronic_signature_trust_services",
        "url": "https://zakon.rada.gov.ua/laws/show/2155-19#Text",
    },
    {
        "doc_id": "law_2210_competition_protection",
        "title": "Закон України «Про захист економічної конкуренції»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "competition",
        "url": "https://zakon.rada.gov.ua/laws/show/2210-14#Text",
    },
    {
        "doc_id": "law_3659_amcu",
        "title": "Закон України «Про Антимонопольний комітет України»",
        "type": "law",
        "authority": "Верховна Рада України",
        "domain": "amcu_complaints_control",
        "url": "https://zakon.rada.gov.ua/laws/show/3659-12#Text",
    },
    {
        "doc_id": "kupap_164_14_procurement_violations",
        "title": "КУпАП, стаття 164-14 «Порушення законодавства про закупівлі»",
        "type": "code_article",
        "authority": "Верховна Рада України",
        "domain": "administrative_liability_procurement",
        "url": "https://zakon.rada.gov.ua/laws/show/8073-10#Text",
        "include_articles": ["164-14"],
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SERVICE_PHRASES = [
    "Ваш броузер застарів!",
    "Нормальне відображення сторінки не можливе",
    "Потрібно включити javascript!",
    "Відбувається форматування тексту!",
    "Зачекайте будь-ласка",
    "Друкувати Допомога Шрифт: або Ctrl + mouse wheel",
    "Друкувати Допомога Шрифт:",
    "або Ctrl + mouse wheel",
    "Повідомити про помилку",
    "Соціальні сервіси та закладки",
    "Офіційний вебпортал парламенту України",
    "Законодавство України",
]

SUPERSCRIPT_DIGITS = str.maketrans({
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
})

APPENDIX_HEADING_PATTERN = re.compile(
    r"^(Додаток|ЗАТВЕРДЖЕНО|ПОРЯДОК|ОСОБЛИВОСТІ|ПЕРЕЛІК)\b"
)
SECTION_HEADING_PATTERN = re.compile(
    r"^(Розділ|Глава)\s+",
    flags=re.IGNORECASE,
)
ARTICLE_HEADING_PATTERN = re.compile(
    r"^Стаття\s+([0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:\s*[-–—−]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)?)\s*\.",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class Section:
    heading: str
    text: str


def to_print_url(url: str) -> str:
    clean_url = url.split("#")[0].rstrip("/")
    if "zakon.rada.gov.ua/laws/show/" in clean_url and not clean_url.endswith("/print"):
        return f"{clean_url}/print"
    return clean_url


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def html_to_text(html: str, selector: Optional[str] = None) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form", "button", "aside"]):
        tag.decompose()

    main = soup.select_one(selector) if selector else None
    main = main or soup.select_one("#Text") or soup.select_one(".text") or soup.select_one("main") or soup.body or soup
    return main.get_text("\n", strip=True)


def clean_text(text: str) -> str:
    for phrase in SERVICE_PHRASES:
        text = text.replace(phrase, " ")

    text = text.replace("\xa0", " ").replace("\u200b", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in {"*", "* * *", "htm zip pdf doc", "Завантажити", "Поділитися"}:
            continue
        lines.append(line)

    return "\n".join(lines).strip()


def remove_leading_site_noise(text: str) -> str:
    markers = [
        "ЗАКОН УКРАЇНИ",
        "КАБІНЕТ МІНІСТРІВ УКРАЇНИ",
        "МІНІСТЕРСТВО ЕКОНОМІКИ УКРАЇНИ",
        "МІНІСТЕРСТВО РОЗВИТКУ ЕКОНОМІКИ",
        "Кодекс України про адміністративні правопорушення",
    ]
    positions = [text.find(marker) for marker in markers if text.find(marker) >= 0]
    return text[min(positions):].strip() if positions else text.strip()


def extract_version_date(html: str, document_text: str) -> Optional[str]:
    full_text = clean_text(html_to_text(html, selector=None))
    candidates = [full_text, document_text]

    patterns = [
        r"Редакція\s+від\s+(\d{2}\.\d{2}\.\d{4})",
        r"Поточна\s+редакція\s+[^\d]{0,50}(\d{2}\.\d{2}\.\d{4})",
        r"станом\s+на\s+(\d{2}\.\d{2}\.\d{4})",
    ]

    for source in candidates:
        for pattern in patterns:
            match = re.search(pattern, source, flags=re.IGNORECASE)
            if match:
                return match.group(1)

    return None


def normalize_article_number(value: str) -> str:
    cleaned = value.translate(SUPERSCRIPT_DIGITS)
    cleaned = re.sub(r"\s+", "", cleaned)
    return (
        cleaned.replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("\u00ad", "")
        .strip()
    )


def filter_articles(text: str, include_articles: list[str]) -> str:
    selected = []

    for article in include_articles:
        normalized = normalize_article_number(article)
        if "-" not in normalized:
            continue

        base, suffix = normalized.split("-", 1)
        start_pattern = re.compile(
            rf"Стаття\s+{base}\s*[-–—−]\s*{suffix}\s*\.",
            flags=re.IGNORECASE,
        )
        match = start_pattern.search(text)
        if not match:
            continue

        next_article_pattern = re.compile(
            r"\n\s*Стаття\s+\d+(?:\s*[-–—−]\s*\d+)?\s*\.",
            flags=re.IGNORECASE,
        )
        next_match = next_article_pattern.search(text, match.end())
        end = next_match.start() if next_match else len(text)
        selected.append(text[match.start():end].strip())

    return "\n\n".join(selected)


def extract_amendments(text: str) -> tuple[str, list[str]]:
    amendments: list[str] = []

    def replace_block(match: re.Match[str]) -> str:
        block = match.group(0).strip()
        if re.search(r"(Із змінами|Вводиться|У тексті|згідно із Законом|доповнено|в редакції|виключено)", block, flags=re.IGNORECASE):
            amendments.append(block)
            return "\n"
        return block

    cleaned = re.sub(r"\{[^{}]{20,2500}\}", replace_block, text, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), amendments


def ensure_article_breaks(text: str) -> str:
    """Гарантує, що кожен заголовок 'Стаття N.' стоїть на власному рядку."""
    pattern = re.compile(
        r"(?<!\n)(?<![\w-])"
        r"(Стаття\s+[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+"
        r"(?:\s*[-–—−]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\s*\.)",
        flags=re.IGNORECASE,
    )
    return pattern.sub(r"\n\1", text)


def is_structural_heading(line: str) -> bool:
    """Чи виглядає рядок як структурний заголовок документа."""
    line = line.strip()
    ci_patterns = [
        r"^Розділ\s+[IVXLCDM\d]+",
        r"^Глава\s+\d+",
        r"^Стаття\s+[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:\s*[-–—−]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\s*\.",
    ]
    if any(re.match(p, line, flags=re.IGNORECASE) for p in ci_patterns):
        return True

    cs_patterns = [
        r"^Додаток\s*\d*",
        r"^ПОРЯДОК\b",
        r"^ОСОБЛИВОСТІ\b",
        r"^ПЕРЕЛІК\b",
        r"^ЗАТВЕРДЖЕНО\b",
    ]
    if any(re.match(p, line) for p in cs_patterns):
        return True
    return False


def extract_heading_from_text(text: str, fallback: str) -> str:
    """Витягує заголовок розділу/статті з ПОЧАТКУ тексту секції.

    Викликається лише на рівні секції (а не для кожного чанка), бо для
    продовжень великих секцій chunk_index > 0 _не_ містить структурного
    заголовка — там лише уривок тексту, з якого помилково можна було б
    взяти фрагмент речення.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:8]:
        if is_structural_heading(line):
            return line[:240]

    match = re.search(
        r"Стаття\s+[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:\s*[-–—−]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)?\s*\.[^\n]{0,220}",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(0).strip()[:240]

    for line in lines[:5]:
        if not line or line.startswith("("):
            continue
        if not line[0].isupper():
            continue
        if len(line) < 12 or len(line) > 240:
            continue
        if line[-1] not in ".!?:":
            continue
        return line

    return fallback


def split_into_sections(text: str, doc_title: str) -> list[Section]:
    """Розбиває документ на секції за структурними заголовками."""
    sections: list[Section] = []
    current_lines: list[str] = []
    current_heading = doc_title

    for line in text.splitlines():
        if is_structural_heading(line) and current_lines:
            section_text = "\n".join(current_lines).strip()
            if len(section_text) < SECTION_MIN_CHARS:
                current_lines.append(line)
                # heading секції оновлюємо на новий, бо він точніше
                # описує наступний змістовий блок
                current_heading = line.strip()
                continue
            heading = extract_heading_from_text(section_text, fallback=current_heading or doc_title)
            sections.append(Section(heading=heading, text=section_text))
            current_lines = [line]
            current_heading = line.strip()
        else:
            current_lines.append(line)

    if current_lines:
        section_text = "\n".join(current_lines).strip()
        heading = extract_heading_from_text(section_text, fallback=current_heading or doc_title)
        sections.append(Section(heading=heading, text=section_text))

    return [section for section in sections if len(section.text.strip()) >= 80]


def find_safe_break(text: str, max_chars: int) -> int:
    window = text[:max_chars]
    separators = ["\n\n", "\n", ". ", "; ", ", ", " "]

    for separator in separators:
        index = window.rfind(separator)
        if index >= int(max_chars * 0.55):
            return index + len(separator)

    return max_chars


def split_large_section(text: str) -> list[str]:
    """Ділить велику секцію на чанки з overlap."""
    if len(text) <= CHUNK_MAX_CHARS:
        return [text.strip()]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        remaining = text[start:]
        if len(remaining) <= CHUNK_MAX_CHARS:
            tail = remaining.strip()
            if not tail:
                break
            # CHANGED: короткий хвіст приклеюємо до попереднього чанка
            if len(tail) < CHUNK_MIN_CHARS and chunks:
                chunks[-1] = (chunks[-1].rstrip() + " " + tail).strip()
            else:
                chunks.append(tail)
            break

        break_at = find_safe_break(remaining, CHUNK_MAX_CHARS)
        chunk = remaining[:break_at].strip()
        if chunk:
            chunks.append(chunk)

        next_start = start + break_at - CHUNK_OVERLAP_CHARS
        if next_start <= start:
            next_start = start + break_at

        # Зсуваємось до межі слова, щоб не починати чанк з обрізаного слова.
        while next_start < len(text) and next_start > 0 and text[next_start - 1].isalnum() and text[next_start].isalnum():
            next_start += 1

        start = next_start

    return chunks


def normalize_inline_text(text: str) -> str:
    """Гарне inline-нормалізування з очищенням артефактів конкатенації."""
    text = re.sub(r"\s+", " ", text).strip()

    # Прибрати пробіли перед розділовими знаками: "слово ." → "слово."
    text = re.sub(r"\s+([\.,;:!?])", r"\1", text)

    # ":." -> ":", "?." -> "?", "!." -> "!"
    text = re.sub(r"([:!?]) *\.", r"\1", text)
    # ";." -> ";"
    text = re.sub(r";\s*\.", ";", text)
    # ",." -> "."
    text = re.sub(r",\s*\.", ".", text)
    # ".." (але не "...") -> "."
    text = re.sub(r"(?<!\.)\.\.(?!\.)", ".", text)
    # «слово  слово» подвійні пробіли
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def section_article_from_heading(heading: str) -> Optional[str]:
    """Якщо заголовок секції — Стаття N, повертає номер N (нормалізований).

    Використовується для stateful tracking: усі чанки секції успадкують
    цей номер, навіть якщо в самому тексті чанка слів "Стаття N" немає.
    """
    if not heading:
        return None
    match = ARTICLE_HEADING_PATTERN.match(heading.strip())
    if not match:
        return None
    return normalize_article_number(match.group(1))


def resets_article_context(heading: str) -> bool:
    """Повертає True, якщо при зустрічі цього heading треба скинути
    "поточну статтю" на None.

    Спрацьовує для додатків (Додаток, ЗАТВЕРДЖЕНО, ПОРЯДОК, ПЕРЕЛІК тощо)
    і для нових Розділів/Глав, які можуть стояти між статтями попереднього
    та наступного блоку.
    """
    if not heading:
        return False
    return bool(APPENDIX_HEADING_PATTERN.match(heading.strip())) or bool(
        SECTION_HEADING_PATTERN.match(heading.strip())
    )


def extract_legal_numbers(
    text: str,
    inherited_article: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Витягує article/part/paragraph номери з тексту чанка."""
    article_match = re.search(
        r"Стаття\s+([0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:\s*[-–—−]\s*[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]+)?)\s*\.",
        text,
        flags=re.IGNORECASE,
    )

    if article_match:
        article_number = normalize_article_number(article_match.group(1))
    else:
        article_number = inherited_article

    part_number = None
    paragraph_number = None

    # Шукати part_number/paragraph_number після першого "Стаття N." (якщо
    # вона є в тексті), інакше — від початку тексту чанка.
    search_window = (
        text[article_match.end(): article_match.end() + 1200] if article_match else text
    )

    part_match = re.search(r"(?:^|\n|\s)(\d+)\.\s+", search_window)
    if part_match:
        part_number = part_match.group(1)

    paragraph_match = re.search(r"(?:^|\n|\s)(\d+)\)\s+", search_window)
    if paragraph_match:
        paragraph_number = paragraph_match.group(1)

    return {
        "article_number": article_number,
        "part_number": part_number,
        "paragraph_number": paragraph_number,
    }


def clean_heading_for_breadcrumb(heading: str) -> str:
    """Готує heading до вставки у breadcrumb."""
    cleaned = heading.strip()
    cleaned = re.sub(r"[\s;,:\.]+$", "", cleaned)
    if len(cleaned) > 100:
        cleaned = cleaned[:100].rsplit(" ", 1)[0]
    return cleaned


def is_meaningful_heading(heading: str) -> bool:
    """True, якщо heading — це справжній структурний заголовок, а не
    обірваний фрагмент речення."""
    if not heading:
        return False
    stripped = heading.strip()
    if not stripped:
        return False
    # Структурні маркери — точно валідні
    if is_structural_heading(stripped):
        return True
    # Має починатися з великої літери (інакше — фрагмент)
    if not stripped[0].isupper():
        return False
    # Має бути розумної довжини
    if len(stripped) > 200:
        return False
    return True


def build_breadcrumb(
    doc_title: str,
    version_date: Optional[str],
    heading: str,
    legal_numbers: dict[str, Optional[str]],
) -> str:
    """Будує breadcrumb для контексту."""
    parts = [doc_title]

    if version_date:
        parts.append(f"редакція від {version_date}")

    if legal_numbers.get("article_number"):
        parts.append(f"стаття {legal_numbers['article_number']}")
    elif is_meaningful_heading(heading):
        parts.append(clean_heading_for_breadcrumb(heading))

    if legal_numbers.get("part_number"):
        parts.append(f"частина/пункт {legal_numbers['part_number']}")

    if legal_numbers.get("paragraph_number"):
        parts.append(f"підпункт/абзац {legal_numbers['paragraph_number']}")

    return ". ".join(parts)


def build_chunks(text: str, doc: dict[str, Any], version_date: Optional[str]) -> list[dict[str, Any]]:
    """Будує чанки документа зі stateful tracking номера статті."""
    chunks: list[dict[str, Any]] = []
    current_article: Optional[str] = None

    for section_index, section in enumerate(split_into_sections(text, doc_title=doc["title"])):
        # Оновлення стану article на межі секції
        article_from_section = section_article_from_heading(section.heading)
        if article_from_section is not None:
            current_article = article_from_section
        elif resets_article_context(section.heading):
            current_article = None

        section_chunks = split_large_section(section.text)

        for chunk_index, chunk_text in enumerate(section_chunks):
            clean_chunk = normalize_inline_text(chunk_text)
            heading = section.heading

            legal_numbers = extract_legal_numbers(
                chunk_text,
                inherited_article=current_article,
            )
            breadcrumb = build_breadcrumb(doc["title"], version_date, heading, legal_numbers)

            chunks.append({
                "section_index": section_index,
                "chunk_index": chunk_index,
                "section_heading": heading,
                "breadcrumb": breadcrumb,
                "text": clean_chunk,
                **legal_numbers,
            })

    return chunks


def make_chunk_id(doc_id: str, text: str, index: int) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{index}_{digest}"


def deduplicate_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """прибирає чанки з повністю ідентичним текстом."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for chunk in chunks:
        text_key = chunk["text"].strip()
        if text_key in seen:
            continue
        seen.add(text_key)
        result.append(chunk)
    return result


def validate_text(doc: dict[str, Any], text: str, version_date: Optional[str]) -> None:
    min_length = 250 if "include_articles" in doc else 1000
    if len(text) < min_length:
        raise ValueError(f"Too little text extracted. Length: {len(text)}")

    if not version_date:
        raise ValueError("Could not parse version_date from zakon.rada.gov.ua page")

    forbidden = [
        "Ваш броузер застарів",
        "Нормальне відображення сторінки не можливе",
        "Потрібно включити javascript",
        "Друкувати Допомога Шрифт",
        "Ctrl + mouse wheel",
    ]
    for phrase in forbidden:
        if phrase in text:
            raise ValueError(f"Garbage text detected: {phrase}")


def process_document(doc: dict[str, Any]) -> list[dict[str, Any]]:
    source_url = to_print_url(doc["url"])
    html = fetch_html(source_url)

    text = html_to_text(html, selector="#Text")
    text = remove_leading_site_noise(text)
    text = clean_text(text)

    version_date = extract_version_date(html, text)

    if "include_articles" in doc:
        text = filter_articles(text, doc["include_articles"])
        text = clean_text(text)

    text, amendments = extract_amendments(text)
    text = clean_text(text)
    text = ensure_article_breaks(text)
    validate_text(doc, text, version_date)

    chunks = build_chunks(text, doc, version_date)
    if not chunks:
        raise ValueError("No chunks created")

    chunks = deduplicate_chunks(chunks)

    source_host = urlparse(source_url).netloc
    fetched_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        records.append({
            "id": make_chunk_id(doc["doc_id"], chunk["text"], index),
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "type": doc["type"],
            "authority": doc["authority"],
            "domain": doc["domain"],
            "source": source_host,
            "source_url": source_url,
            "version_date": version_date,
            "date_fetched": fetched_at,
            "section_index": chunk["section_index"],
            "chunk_index": chunk["chunk_index"],
            "section_heading": chunk["section_heading"],
            "breadcrumb": chunk["breadcrumb"],
            "article_number": chunk["article_number"],
            "part_number": chunk["part_number"],
            "paragraph_number": chunk["paragraph_number"],
            "doc_amendments_removed_count": len(amendments),
            "text": chunk["text"],
        })

    return records


def save_failed_report(failed_documents: list[dict[str, Any]]) -> Optional[Path]:
    if not failed_documents:
        return None

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc)
    report_path = REPORTS_DIR / f"failed_documents_{generated_at.strftime('%Y-%m-%d_%H-%M-%S')}.json"

    report = {
        "generated_at": generated_at.isoformat(),
        "failed_count": len(failed_documents),
        "failed_documents": failed_documents,
    }

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    return report_path


def build_dataset() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    failed_documents: list[dict[str, Any]] = []

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for doc in DOCUMENTS:
            try:
                print(f"Fetching: {doc['title']}")
                print(f"URL: {to_print_url(doc['url'])}")

                records = process_document(doc)

                for record in records:
                    output_file.write(json.dumps(record, ensure_ascii=False) + "\n")

                total_chunks += len(records)
                print(f"OK: {len(records)} chunks\n")
                time.sleep(REQUEST_DELAY_SECONDS)

            except Exception as error:
                print(f"FAILED: {doc['doc_id']}")
                print(f"Reason: {error}\n")
                failed_documents.append({
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "url": doc["url"],
                    "error": str(error),
                })

    report_path = save_failed_report(failed_documents)

    print("Done.")
    print(f"Chunks created: {total_chunks}")
    print(f"Output: {OUTPUT_PATH}")

    if report_path:
        print(f"Failed report: {report_path}")


if __name__ == "__main__":
    build_dataset()