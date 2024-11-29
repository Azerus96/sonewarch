# main.py

import asyncio
import logging.config
from flask import Flask
from flask_sock import Sock
from config.settings import get_config, LOGGING_CONFIG
from app.web.routes import web
from app.web.websocket import sock

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Загрузка конфигурации
    config = get_config() if config_name is None else config[config_name]
    app.config.from_object(config)
    
    # Настройка логирования
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Инициализация WebSocket
    sock.init_app(app)
    
    # Регистрация blueprints
    app.register_blueprint(web)
    
    return app

def run_app():
    app = create_app()
    
    # Настройка для асинхронной работы
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=app.config['DEBUG']
        )
    finally:
        loop.close()

if __name__ == '__main__':
    run_app()
