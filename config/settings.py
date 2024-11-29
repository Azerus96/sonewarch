# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    DEBUG = False
    TESTING = False

def get_config():
    return Config
