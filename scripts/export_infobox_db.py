#!/usr/bin/env python3
import argparse
import html
import json
import hashlib
import logging
import re
import subprocess
from collections import defaultdict  # Додано цей рядок
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterator, List, Optional, Dict

# Конфігурація логування
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RAGChunk:
    """Модель даних для одного чанку знань."""
    id: str
    doc_id: str
    title: str
    type: str
    date_published: str
    tags: List[str]
    chunk_index: int
    text: str


class ProzorroExporter:
    """Експортер даних Prozorro у формат JSONL для RAG-систем."""

    CHUNK_SIZE = 2000
    CHUNK_OVERLAP = 300

    CONTENT_MAP = {
        "articles.view": "articles.jsonl",
        "news.view": "news.jsonl",
        "news-mert.view": "news_mert.jsonl",
        "faq.view": "faq.jsonl",
        "courses.view": "courses.jsonl",
    }

    def __init__(self, output_dir: str):
        self.output_path = Path(output_dir)
        self.db_command = [
            "docker", "compose", "exec", "-T", "mariadb", "mysql",
            "--default-character-set=utf8mb4", "-uprozorro", "-pprozorro",
            "-D", "prozorro", "--batch", "--skip-column-names", "--silent"
        ]

    def _generate_id(self, salt: str) -> str:
        """Створює унікальний хеш для чанку."""
        return hashlib.md5(salt.encode()).hexdigest()[:12]

    def _clean_html(self, raw_html: str) -> str:
        """Очищує HTML та нормалізує текст."""
        if not raw_html: return ""
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|section|article|h[1-6]|tr|li)>", "\n", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html.unescape(text)
        return re.sub(r"[ \t]+", " ", text).strip()

    def _split_text(self, text: str) -> List[str]:
        """Розбиває текст на чанки з перекриттям[cite: 1, 2]."""
        if len(text) <= self.CHUNK_SIZE:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunks.append(text[start:end])
            start += (self.CHUNK_SIZE - self.CHUNK_OVERLAP)
            if end >= len(text): break
        return chunks

    def _run_query(self, sql: str) -> Iterator[List[str]]:
        """Виконує SQL запит та безпечно декодує HEX[cite: 10]."""
        try:
            process = subprocess.Popen(
                [*self.db_command, "-e", sql],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace"
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"MySQL Error: {stderr}")
                return

            for line in stdout.splitlines():
                row = line.split("\t")
                if not row or not any(row): continue

                decoded = []
                for val in row:
                    if val and all(c in "0123456789abcdefABCDEF" for c in val):
                        try:
                            decoded.append(bytes.fromhex(val).decode("utf-8", errors="replace"))
                        except ValueError:
                            decoded.append(val)
                    else:
                        decoded.append(val or "")
                yield decoded
        except Exception as e:
            logger.error(f"Execution error: {e}")

    def process_content(self) -> Dict[str, int]:
        """Обробляє основні статті та новини[cite: 3, 10]."""
        sql = """
              SELECT HEX(CAST(m.id AS CHAR)), \
                     HEX(t.route), \
                     HEX(IFNULL(mt.name, '')),
                     HEX(CAST(IFNULL(mt.date, m.created_at) AS CHAR)),
                     HEX(IFNULL(mt.description, '')), \
                     HEX(IFNULL(mt.text, '')),
                     HEX(IFNULL((SELECT GROUP_CONCAT(tags.name) \
                                 FROM main_tag \
                                          JOIN tags ON tags.id = main_tag.tag_id
                                 WHERE main_tag.main_id = m.id), ''))
              FROM main m
                       JOIN type t ON t.id = m.type_id
                       LEFT JOIN main_translations mt ON mt.main_id = m.id AND mt.locale = 'ua' \
              """
        stats = defaultdict(int)
        for row in self._run_query(sql):
            rec_id, route, title, date, desc, body, tags_raw = row
            fname = self.CONTENT_MAP.get(route)
            if not fname: continue

            tags = [t.strip() for t in tags_raw.split(',')] if tags_raw else []
            full_text = self._clean_html(f"{desc}\n\n{body}")
            if not full_text: continue

            breadcrumb = f"Джерело: Prozorro. Розділ: {route.split('.')[0]}. Стаття: {title}. Дата: {date}.\n\n"

            for idx, fragment in enumerate(self._split_text(full_text)):
                chunk_text = breadcrumb + fragment
                chunk = RAGChunk(
                    id=f"c_{rec_id}_{idx}_{self._generate_id(chunk_text)}",
                    doc_id=rec_id, title=title, type="article",
                    date_published=date, tags=tags, chunk_index=idx, text=chunk_text
                )
                self._save(fname, chunk)
                stats[fname] += 1
        return stats

    def process_comments(self) -> int:
        """Експортує коментарі користувачів."""
        sql = """
              SELECT HEX(CAST(c.id AS CHAR)), \
                     HEX(CAST(c.post_id AS CHAR)),
                     HEX(CAST(IFNULL(c.parent_id, 0) AS CHAR)), \
                     HEX(CAST(c.created_at AS CHAR)),
                     HEX(IFNULL(mt.name, 'Без назви')), \
                     HEX(IFNULL(c.body, ''))
              FROM comments c
                       LEFT JOIN main_translations mt ON mt.main_id = c.post_id AND mt.locale = 'ua'
              WHERE c.approved = 1 \
              """
        count = 0
        for row in self._run_query(sql):
            c_id, post_id, p_id, date, post_title, body = row
            text = self._clean_html(body)
            if not text: continue

            context = f"Стаття: {post_title}. Коментар від {date}.\nТекст: {text}"
            if p_id != "0":
                context = f"Відповідь на гілку #{p_id}. {context}"

            chunk = RAGChunk(
                id=f"com_{c_id}", doc_id=post_id, title=f"Коментар до {post_title}",
                type="comment", date_published=date, tags=["коментар"],
                chunk_index=0, text=context
            )
            self._save("comments.jsonl", chunk)
            count += 1
        return count

    def _save(self, filename: str, chunk: RAGChunk):
        """Зберігає об'єкт у файл."""
        with (self.output_path / filename).open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    def run(self):
        """Запуск повного циклу експорту."""
        self.output_path.mkdir(parents=True, exist_ok=True)
        for f in self.output_path.glob("*.jsonl"): f.unlink()

        logger.info("Starting content export...")
        c_stats = self.process_content()

        logger.info("Starting comments export...")
        com_count = self.process_comments()

        logger.info(f"Done. Files: {dict(c_stats)}, comments.jsonl: {com_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output-dir", default="data/infobox")
    args = parser.parse_args()
    ProzorroExporter(args.output_dir).run()