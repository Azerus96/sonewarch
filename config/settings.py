# config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

class BaseConfig:
    # Application Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = False
    TESTING = False
    
    # Search Engine Settings
    MAX_PAGES = 100
    MAX_DEPTH = 10
    CONCURRENT_REQUESTS = 20
    REQUEST_TIMEOUT = 30
    MAX_CONTENT_SIZE = 500_000
    
    # Redis Settings
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # Rate Limiting
    REQUESTS_PER_SECOND = 2
    BURST_SIZE = 5
    
    # WebSocket Settings
    WS_UPDATE_INTERVAL = 0.5

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    CONCURRENT_REQUESTS = 10

class ProductionConfig(BaseConfig):
    # Production-specific settings
    CONCURRENT_REQUESTS = 50
    REQUEST_TIMEOUT = 60
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

class TestingConfig(BaseConfig):
    TESTING = True
    CONCURRENT_REQUESTS = 5
    MAX_PAGES = 10

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# config/settings.py (продолжение)

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

# Глобальные настройки логирования
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'search_engine.log',
            'mode': 'a',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
