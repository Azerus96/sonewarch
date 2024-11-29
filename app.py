# app.py
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
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    return app

app = create_app()
