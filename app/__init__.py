# app/__init__.py
from flask import Flask
from flask_sock import Sock
from config.settings import get_config
import logging.config
from .web.routes import web
from .web.websocket import sock

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Загрузка конфигурации
    config = get_config() if config_name is None else config[config_name]
    app.config.from_object(config)
    
    # Инициализация WebSocket
    sock.init_app(app)
    
    # Регистрация blueprints
    app.register_blueprint(web)
    
    return app
