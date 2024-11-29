# app/utils/text_ranking.py
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
import math

@dataclass
class RankingMetrics:
    title_score: float
    meta_score: float
    headers_score: float
    content_score: float
    position_score: float
    total_score: float

class TextRanker:
    def __init__(self):
        self.weights = {
            'title': 3.0,
            'meta': 2.0,
            'headers': 1.5,
            'content': 1.0,
            'position': 0.5
        }
        
    def calculate_relevance(self, 
                          matches: List[str], 
                          title: str, 
                          meta_description: str, 
                          headers: List[str], 
                          search_term: str) -> RankingMetrics:
        """
        Вычисляет релевантность текста на основе различных метрик
        """
        # Нормализация поискового запроса
        search_term = search_term.lower()
        
        # Вычисление отдельных метрик
        title_score = self._calculate_title_score(title, search_term)
        meta_score = self._calculate_meta_score(meta_description, search_term)
        headers_score = self._calculate_headers_score(headers, search_term)
        content_score = self._calculate_content_score(matches, search_term)
        position_score = self._calculate_position_score(matches)
        
        # Вычисление общего счета
        total_score = (
            title_score * self.weights['title'] +
            meta_score * self.weights['meta'] +
            headers_score * self.weights['headers'] +
            content_score * self.weights['content'] +
            position_score * self.weights['position']
        )
        
        return RankingMetrics(
            title_score=title_score,
            meta_score=meta_score,
            headers_score=headers_score,
            content_score=content_score,
            position_score=position_score,
            total_score=total_score
        )
    
    def _calculate_title_score(self, title: str, search_term: str) -> float:
        """Оценка релевантности заголовка"""
        if not title:
            return 0.0
            
        title = title.lower()
        # Точное совпадение в заголовке
        if search_term in title:
            return 1.0
        
        # Частичное совпадение слов
        search_words = set(search_term.split())
        title_words = set(title.split())
        matching_words = search_words.intersection(title_words)
        
        return len(matching_words) / len(search_words)
    
    def _calculate_meta_score(self, meta_description: str, search_term: str) -> float:
        """Оценка релевантности мета-описания"""
        if not meta_description:
            return 0.0
            
        meta_description = meta_description.lower()
        if search_term in meta_description:
            return 1.0
            
        # Анализ частичных совпадений
        search_words = set(search_term.split())
        meta_words = set(meta_description.split())
        matching_words = search_words.intersection(meta_words)
        
        return len(matching_words) / len(search_words)
    
    def _calculate_headers_score(self, headers: List[str], search_term: str) -> float:
        """Оценка релевантности заголовков"""
        if not headers:
            return 0.0
            
        scores = []
        for header in headers:
            header = header.lower()
            if search_term in header:
                scores.append(1.0)
            else:
                search_words = set(search_term.split())
                header_words = set(header.split())
                matching_words = search_words.intersection(header_words)
                scores.append(len(matching_words) / len(search_words))
                
        return max(scores) if scores else 0.0
    
    def _calculate_content_score(self, matches: List[str], search_term: str) -> float:
        """Оценка релевантности контента"""
        if not matches:
            return 0.0
            
        # Учитываем количество совпадений и их качество
        total_score = 0.0
        for match in matches:
            # Точное совпадение
            if search_term in match.lower():
                total_score += 1.0
            # Частичное совпадение
            else:
                search_words = set(search_term.split())
                match_words = set(match.lower().split())
                matching_words = search_words.intersection(match_words)
                total_score += len(matching_words) / len(search_words)
                
        return min(total_score / len(matches), 1.0)
    
    def _calculate_position_score(self, matches: List[str]) -> float:
        """Оценка позиции совпадений в тексте"""
        if not matches:
            return 0.0
            
        # Предполагаем, что matches отсортированы по позиции в тексте
        # Даем больший вес совпадениям в начале текста
        scores = []
        for i, _ in enumerate(matches):
            position_weight = 1.0 / (i + 1)
            scores.append(position_weight)
            
        return sum(scores) / len(scores)
