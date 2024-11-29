# app/core/parser.py

from typing import Optional, Dict
from bs4 import BeautifulSoup
import logging
from dataclasses import dataclass

@dataclass
class ParsedContent:
    title: str
    text: str
    meta_description: str
    headers: list[str]
    raw_html: str

class Parser:
    def __init__(self):
        self.parser = 'lxml'
        self.cache: Dict[str, ParsedContent] = {}
        
    async def parse(self, content: str) -> Optional[ParsedContent]:
        try:
            # Проверяем кэш
            content_hash = hash(content)
            if content_hash in self.cache:
                return self.cache[content_hash]

            soup = BeautifulSoup(content, self.parser)
            
            # Удаляем ненужные элементы
            for tag in soup(['script', 'style', 'iframe', 'noscript']):
                tag.decompose()

            parsed = ParsedContent(
                title=self._get_title(soup),
                text=self._get_main_text(soup),
                meta_description=self._get_meta_description(soup),
                headers=self._get_headers(soup),
                raw_html=content
            )
            
            # Кэшируем результат
            self.cache[content_hash] = parsed
            return parsed
            
        except Exception as e:
            logging.error(f"Parsing error: {e}")
            return None

    def _get_title(self, soup: BeautifulSoup) -> str:
        if soup.title:
            return soup.title.string.strip()
        if h1 := soup.find('h1'):
            return h1.get_text().strip()
        return "Untitled"

    def _get_main_text(self, soup: BeautifulSoup) -> str:
        text_elements = []
        for tag in soup.find_all(['p', 'div', 'article', 'section']):
            if text := tag.get_text().strip():
                text_elements.append(text)
        return ' '.join(text_elements)

    def _get_meta_description(self, soup: BeautifulSoup) -> str:
        meta = soup.find('meta', attrs={'name': 'description'})
        return meta.get('content', '') if meta else ''

    def _get_headers(self, soup: BeautifulSoup) -> list[str]:
        headers = []
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            if text := tag.get_text().strip():
                headers.append(text)
        return headers
