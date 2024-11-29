# app/utils/error_handler.py
import asyncio
import logging
import functools
import traceback
from typing import Type, Callable, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict, deque
import aiohttp

@dataclass
class ErrorDetails:
    error_type: str
    message: str
    timestamp: datetime
    traceback: str
    context: dict

class ErrorHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_callbacks: list[Callable] = []
        
    def register_callback(self, callback: Callable):
        """Регистрация callback-функции для обработки ошибок"""
        self.error_callbacks.append(callback)
        
    def handle_error(self, error: Exception, context: dict = None) -> ErrorDetails:
        """Обработка ошибки и создание отчета"""
        error_details = ErrorDetails(
            error_type=type(error).__name__,
            message=str(error),
            timestamp=datetime.now(),
            traceback=traceback.format_exc(),
            context=context or {}
        )
        
        # Логирование ошибки
        self.logger.error(
            f"Error occurred: {error_details.error_type}\n"
            f"Message: {error_details.message}\n"
            f"Context: {error_details.context}\n"
            f"Traceback: {error_details.traceback}"
        )

  # app/utils/error_handler.py (продолжение)

        # Выполнение всех зарегистрированных обработчиков
        for callback in self.error_callbacks:
            try:
                callback(error_details)
            except Exception as e:
                self.logger.error(f"Error in error callback: {str(e)}")
                
        return error_details

    def catch_errors(self, error_types: tuple[Type[Exception]] = (Exception,)):
        """Декоратор для перехвата и обработки ошибок"""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except error_types as e:
                    context = {
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                    return self.handle_error(e, context)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except error_types as e:
                    context = {
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                    return self.handle_error(e, context)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

# Создаем глобальный экземпляр обработчика ошибок
error_handler = ErrorHandler()

# Декораторы для удобного использования
def handle_errors(error_types: tuple[Type[Exception]] = (Exception,)):
    return error_handler.catch_errors(error_types)

class SearchEngineError(Exception):
    """Базовый класс для ошибок поискового движка"""
    pass

class ConnectionError(SearchEngineError):
    """Ошибка соединения"""
    pass

class ParsingError(SearchEngineError):
    """Ошибка парсинга"""
    pass

class RateLimitError(SearchEngineError):
    """Ошибка превышения лимита запросов"""
    pass

# Пример использования:
@handle_errors((ConnectionError, ParsingError))
async def fetch_page(url: str) -> str:
    """
    Пример функции с обработкой ошибок
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ConnectionError(f"Failed to fetch page: {response.status}")
                return await response.text()
    except aiohttp.ClientError as e:
        raise ConnectionError(f"Connection error: {str(e)}")

# Регистрация обработчика для отправки ошибок в мониторинг
async def send_to_monitoring(error_details: ErrorDetails):
    """
    Пример callback-функции для отправки ошибок в систему мониторинга
    """
    try:
        # Здесь может быть интеграция с Sentry, Prometheus и т.д.
        logging.info(f"Sending error to monitoring: {error_details}")
    except Exception as e:
        logging.error(f"Failed to send error to monitoring: {str(e)}")

# Регистрируем обработчик
error_handler.register_callback(send_to_monitoring)

# Утилиты для работы с ошибками
def format_error_message(error: Exception, context: dict = None) -> str:
    """
    Форматирование сообщения об ошибке для пользователя
    """
    base_message = str(error)
    if isinstance(error, ConnectionError):
        return f"Ошибка подключения: {base_message}"
    elif isinstance(error, ParsingError):
        return f"Ошибка обработки страницы: {base_message}"
    elif isinstance(error, RateLimitError):
        return f"Превышен лимит запросов: {base_message}"
    return f"Произошла ошибка: {base_message}"

def is_retryable_error(error: Exception) -> bool:
    """
    Определяет, можно ли повторить операцию после данной ошибки
    """
    return isinstance(error, (ConnectionError, RateLimitError))

class ErrorMetrics:
    """
    Класс для сбора метрик об ошибках
    """
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_errors = deque(maxlen=100)

    def record_error(self, error_details: ErrorDetails):
        """
        Записать информацию об ошибке
        """
        self.error_counts[error_details.error_type] += 1
        self.last_errors.append(error_details)

    def get_statistics(self) -> dict:
        """
        Получить статистику по ошибкам
        """
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_types': dict(self.error_counts),
            'recent_errors': len(self.last_errors)
        }

# Создаем глобальный экземпляр для метрик
error_metrics = ErrorMetrics()

# Регистрируем обработчик для сбора метрик
error_handler.register_callback(error_metrics.record_error)
