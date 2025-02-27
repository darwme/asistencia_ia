import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://asistencia_user:dp0Kst6GUCJczdy1UlLeEucdC7BceLp3@dpg-cv094dfnoe9s73d1gljg-a.oregon-postgres.render.com/asistenciafisi2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    