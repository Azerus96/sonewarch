# main.py
import os
from flask import Flask
from flask_sock import Sock
from config.settings import get_config

def create_app():
    app = Flask(__name__)
    
    # Загрузка конфигурации
    config = get_config()
    app.config.from_object(config)
    
    # Инициализация WebSocket
    sock = Sock(app)
    
    # Регистрация маршрутов
    from app.web.routes import web
    app.register_blueprint(web)
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
