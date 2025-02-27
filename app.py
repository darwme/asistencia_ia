import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object('config.Config')

# Configuración de CORS
CORS(app, resources={r"/*": {"origins": ["https://asistencia-vlqb.onrender.com"], "supports_credentials": True}})

db = SQLAlchemy(app)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    paternal_surname = db.Column(db.String(100), nullable=False)
    maternal_surname = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    group_col = db.Column(db.String(50))
    password = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), default='student')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(50), default='on_time')

@app.route('/')
def index():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(debug=os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'))
