# app/core/text_processor.py

from typing import Optional, List
import re
from dataclasses import dataclass
from .parser import ParsedContent
from ..utils.text_ranking import TextRanker

@dataclass
class TextMatch:
    text: str
    position: int
    context: str
    relevance: float

class TextProcessor:
    def __init__(self):
        self.ranker = TextRanker()
        self.context_size = 100  # символов до и после совпадения
        
    async def process(self, url: str, content: ParsedContent, search_term: str) -> Optional[SearchResult]:
        try:
            # Нормализация поискового запроса
            normalized_term = search_term.lower()
            
            # Поиск совпадений
            matches = self._find_matches(content, normalized_term)
            if not matches:
                return None

            # Расчет релевантности
            relevance = self.ranker.calculate_relevance(
                matches=matches,
                title=content.title,
                meta_description=content.meta_description,
                headers=content.headers,
                search_term=search_term
            )

            # Выбор лучшего контекста
            best_match = max(matches, key=lambda m: m.relevance)
            
            return SearchResult(
                url=url,
                title=content.title,
                context=best_match.context,
                count=len(matches),
                relevance=relevance
            )
            
        except Exception as e:
            logging.error(f"Text processing error: {e}")
            return None

    def _find_matches(self, content: ParsedContent, search_term: str) -> List[TextMatch]:
        matches = []
        text = content.text.lower()
        
        for match in re.finditer(re.escape(search_term), text):
            start = max(0, match.start() - self.context_size)
            end = min(len(text), match.end() + self.context_size)
            
            context = text[start:end]
            relevance = self._calculate_match_relevance(match, content)
            
            matches.append(TextMatch(
                text=match.group(),
                position=match.start(),
                context=context,
                relevance=relevance
            ))
            
        return matches

    def _calculate_match_relevance(self, match, content: ParsedContent) -> float:
        # Базовая релевантность
        relevance = 1.0
        
        # Увеличиваем релевантность если совпадение ближе к началу текста
        position_factor = 1 - (match.start() / len(content.text))
        relevance *= (1 + position_factor)
        
        # Увеличиваем если совпадение в заголовке
        if any(match.group() in h.lower() for h in content.headers):
            relevance *= 1.5
            
        return relevance
