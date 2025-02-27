import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://asistencia_user:n7GZFVZzgE5QyEnP7V9fDgLPwMfYN5qZ@dpg-cv0fcf8gph6c73casoh0-a.oregon-postgres.render.com/asistencia_ia')
    SQLALCHEMY_TRACK_MODIFICATIONS = False