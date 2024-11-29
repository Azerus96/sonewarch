# app/web/websocket.py

from flask_sock import Sock
import json
import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime
from ..core.search_engine import SearchEngine
from ..utils.error_handler import handle_errors
from ..services.state_manager import StateManager

# Инициализация веб-сокета
sock = Sock()

class WebSocketManager:
    def __init__(self):
        self.search_engine = SearchEngine()
        self.state_manager = StateManager()
        self.active_connections: Dict[str, set] = {}
        self.logger = logging.getLogger(__name__)

    async def handle_connection(self, ws, search_id: str):
        """Обработка WebSocket соединения"""
        try:
            # Регистрация соединения
            if search_id not in self.active_connections:
                self.active_connections[search_id] = set()
            self.active_connections[search_id].add(ws)

            try:
                while True:
                    # Получение текущего состояния поиска
                    state = await self.state_manager.get_state(search_id)
                    if not state:
                        await self.send_error(ws, "Search not found")
                        break

                    # Отправка состояния клиенту
                    await self.send_state(ws, state)

                    # Проверка завершения поиска
                    if state['current_status'] in ['completed', 'error']:
                        break

                    # Пауза перед следующим обновлением
                    await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"WebSocket error for search {search_id}: {str(e)}")
                await self.send_error(ws, "Connection error occurred")

        finally:
            # Очистка соединения при завершении
            if search_id in self.active_connections:
                self.active_connections[search_id].remove(ws)
                if not self.active_connections[search_id]:
                    del self.active_connections[search_id]

    @handle_errors()
    async def send_state(self, ws, state: dict):
        """Отправка состояния поиска клиенту"""
        try:
            await ws.send(json.dumps({
                "type": "state_update",
                "data": state,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            self.logger.error(f"Error sending state: {str(e)}")
            raise

    @handle_errors()
    async def send_error(self, ws, message: str):
        """Отправка сообщения об ошибке клиенту"""
        try:
            await ws.send(json.dumps({
                "type": "error",
                "message": message,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            self.logger.error(f"Error sending error message: {str(e)}")
            raise

    async def broadcast_to_search(self, search_id: str, message: dict):
        """Отправка сообщения всем клиентам определенного поиска"""
        if search_id in self.active_connections:
            for ws in self.active_connections[search_id]:
                try:
                    await ws.send(json.dumps(message))
                except Exception as e:
                    self.logger.error(f"Broadcast error: {str(e)}")

    async def close_all_connections(self, search_id: str):
        """Закрытие всех соединений для определенного поиска"""
        if search_id in self.active_connections:
            for ws in self.active_connections[search_id]:
                try:
                    await ws.close()
                except Exception as e:
                    self.logger.error(f"Error closing connection: {str(e)}")
            del self.active_connections[search_id]

# Создание экземпляра WebSocket менеджера
ws_manager = WebSocketManager()

@sock.route('/ws/<search_id>')
@handle_errors()
async def websocket_endpoint(ws, search_id: str):
    """WebSocket endpoint для обновлений прогресса поиска"""
    try:
        await ws_manager.handle_connection(ws, search_id)
    except Exception as e:
        logging.error(f"WebSocket endpoint error: {str(e)}")
        try:
            await ws.send(json.dumps({
                "type": "error",
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat()
            }))
        except:
            pass
        finally:
            await ws.close()

# Вспомогательные функции для работы с WebSocket
async def notify_search_started(search_id: str):
    """Уведомление о начале поиска"""
    await ws_manager.broadcast_to_search(search_id, {
        "type": "search_started",
        "search_id": search_id,
        "timestamp": datetime.now().isoformat()
    })

async def notify_search_completed(search_id: str, results: list):
    """Уведомление о завершении поиска"""
    await ws_manager.broadcast_to_search(search_id, {
        "type": "search_completed",
        "search_id": search_id,
        "results": results,
        "timestamp": datetime.now().isoformat()
    })

async def notify_search_error(search_id: str, error: str):
    """Уведомление об ошибке поиска"""
    await ws_manager.broadcast_to_search(search_id, {
        "type": "search_error",
        "search_id": search_id,
        "error": error,
        "timestamp": datetime.now().isoformat()
    })

# Обработчик для очистки неактивных соединений
async def cleanup_inactive_connections():
    """Периодическая очистка неактивных соединений"""
    while True:
        try:
            for search_id in list(ws_manager.active_connections.keys()):
                state = await ws_manager.state_manager.get_state(search_id)
                if not state or state['current_status'] in ['completed', 'error']:
                    await ws_manager.close_all_connections(search_id)
            await asyncio.sleep(300)  # Проверка каждые 5 минут
        except Exception as e:
            logging.error(f"Cleanup error: {str(e)}")
            await asyncio.sleep(60)

# Запуск очистки неактивных соединений
asyncio.create_task(cleanup_inactive_connections())
