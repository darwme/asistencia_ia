import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from geopy.distance import geodesic
from datetime import datetime, time

# Cargar variables de entorno desde un archivo .env
load_dotenv()

app = Flask(__name__)

# Variables de entorno
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_super_segura')  # Cambiar en producción
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://asistencia_user:dp0Kst6GUCJczdy1UlLeEucdC7BceLp3@dpg-cv094dfnoe9s73d1gljg-a.oregon-postgres.render.com/asistenciafisi2024')
CORS_ORIGIN = os.environ.get('CORS_ORIGIN', 'https://asistencia-vlqb.onrender.com/')

# Configurar CORS
CORS(
    app,
    resources={r"/*": {"origins": CORS_ORIGIN}},
    supports_credentials=True
)


# Configuración de PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------- MODELOS --------------------
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    paternal_surname = db.Column(db.String(100), nullable=False)
    maternal_surname = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    group_col = db.Column(db.String(50))
    password = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), default='student')  # 'student' o 'teacher'

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # 'on_time', 'late', 'absent', 'outside_campus'
    status = db.Column(db.String(50), default='on_time')

# -------------------- CONFIGURACIÓN --------------------
CAMPUS_COORDINATES = (-12.052977641846182, -77.08569823378284)  # Ejemplo: coordenadas de UNMSM
RADIUS_KM = 0.5

# Rangos de hora
ATTENDANCE_START = time(18, 0, 0)   # 18:00
ATTENDANCE_END = time(18, 30, 0)    # 18:30
LATE_END = time(19, 30, 0)          # 19:30

def is_within_radius(coord1, coord2, radius_km):
    return geodesic(coord1, coord2).kilometers <= radius_km

def determine_status(arrival_time: time):
    """
    Retorna on_time, late o absent según la hora de llegada.
    - on_time: [18:00, 18:30)
    - late:    [18:30, 19:30)
    - absent:  fuera de ese rango
    """
    if arrival_time >= ATTENDANCE_START and arrival_time < ATTENDANCE_END:
        return 'on_time'
    elif arrival_time >= ATTENDANCE_END and arrival_time < LATE_END:
        return 'late'
    else:
        return 'absent'

# -------------------- RUTAS --------------------
@app.route('/initdb', methods=['GET'])
def init_db():
    db.create_all()
    return jsonify({'message': 'Tablas creadas o actualizadas correctamente.'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Faltan credenciales'}), 400

    student = Student.query.filter_by(email=email).first()
    if not student:
        return jsonify({'error': 'Usuario no encontrado'}), 401

    if student.password != password:
        return jsonify({'error': 'Contraseña incorrecta'}), 401

    session['student_id'] = student.id
    session['user_type'] = student.user_type
    return jsonify({'message': 'Login exitoso', 'user_type': student.user_type}), 200

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout exitoso'}), 200

@app.route('/attendance', methods=['POST'])
def register_attendance():
    """
    Valida la ubicación. Si está fuera del campus se marca como outside_campus.
    Si está dentro, se determina si es on_time, late o absent según la hora (UTC).
    """
    if 'student_id' not in session:
        return jsonify({'error': 'No has iniciado sesión'}), 401

    data = request.get_json()
    course = data.get('course')
    lat = data.get('latitude')
    lng = data.get('longitude')

    if not course or lat is None or lng is None:
        return jsonify({'error': 'Datos insuficientes'}), 400

    student_id = session['student_id']

    # Verificar ubicación
    if not is_within_radius(CAMPUS_COORDINATES, (lat, lng), RADIUS_KM):
        outside_att = Attendance(
            student_id=student_id,
            course=course,
            latitude=lat,
            longitude=lng,
            status='outside_campus'
        )
        db.session.add(outside_att)
        db.session.commit()
        return jsonify({'error': 'Estudiante fuera del campus'}), 400

    now_utc = datetime.utcnow()
    arrival_time = now_utc.time()  # Hora actual en UTC

    final_status = determine_status(arrival_time)

    new_att = Attendance(
        student_id=student_id,
        course=course,
        latitude=lat,
        longitude=lng,
        status=final_status
    )
    db.session.add(new_att)
    db.session.commit()

    if final_status == 'absent':
        return jsonify({'error': 'Estás fuera del horario permitido, se marcó como falta'}), 400
    elif final_status == 'late':
        return jsonify({'message': 'Registrado como tarde'}), 200
    else:
        return jsonify({'message': 'Asistencia registrada (on_time)'}), 200

@app.route('/admin/attendance', methods=['GET'])
def get_attendance():
    """
    Retorna:
      - Registro General (todos los registros del ciclo) si no se envía ?date=
      - O el reporte de un día específico (incluyendo los ausentes) si se envía ?date=YYYY-MM-DD
    """
    if 'student_id' not in session or session.get('user_type') != 'teacher':
        return jsonify({'error': 'No autorizado'}), 403

    date_str = request.args.get('date')

    # Registro General: si no se envía ?date=
    if not date_str:
        attendance_list = Attendance.query.all()

        on_time = []
        late = []
        outside = []
        absent_list = []

        for att in attendance_list:
            st = Student.query.get(att.student_id)
            record = {
                'attendance_id': att.id,
                'student_code': st.student_code,
                'first_name': st.first_name,
                'paternal_surname': st.paternal_surname,
                'maternal_surname': st.maternal_surname,
                'timestamp': att.timestamp.isoformat(),
                'status': att.status
            }
            if att.status == 'outside_campus':
                outside.append(record)
            elif att.status == 'late':
                late.append(record)
            elif att.status == 'absent':
                absent_list.append(record)
            else:
                on_time.append(record)

        report = {
            'date': 'all',
            'on_time': on_time,
            'late': late,
            'outside_campus': outside,
            'absent': absent_list
        }
        return jsonify(report), 200

    # Reporte Diario: se procesa ?date=YYYY-MM-DD
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400

    attendance_list = (Attendance.query
                       .filter(db.func.date(Attendance.timestamp) == day)
                       .all())

    on_time = []
    late = []
    outside = []
    absent_list = []

    for att in attendance_list:
        st = Student.query.get(att.student_id)
        record = {
            'attendance_id': att.id,
            'student_code': st.student_code,
            'first_name': st.first_name,
            'paternal_surname': st.paternal_surname,
            'maternal_surname': st.maternal_surname,
            'timestamp': att.timestamp.isoformat(),
            'status': att.status
        }
        if att.status == 'outside_campus':
            outside.append(record)
        elif att.status == 'late':
            late.append(record)
        elif att.status == 'absent':
            absent_list.append(record)
        else:
            on_time.append(record)

    # Marcar como ausentes a quienes no registraron asistencia ese día
    all_students = Student.query.filter_by(user_type='student').all()
    marked_ids = [a.student_id for a in attendance_list]
    for st in all_students:
        if st.id not in marked_ids:
            absent_list.append({
                'attendance_id': None,
                'student_code': st.student_code,
                'first_name': st.first_name,
                'paternal_surname': st.paternal_surname,
                'maternal_surname': st.maternal_surname,
                'timestamp': None,
                'status': 'absent'
            })

    report = {
        'date': date_str,
        'on_time': on_time,
        'late': late,
        'outside_campus': outside,
        'absent': absent_list
    }
    return jsonify(report), 200

@app.route('/admin/update_status', methods=['POST'])
def update_attendance_status():
    """
    Permite al profesor actualizar el status de un registro de asistencia (o crear uno).
    Request body: { attendance_id, new_status, student_code (opcional) }
    """
    if 'student_id' not in session or session.get('user_type') != 'teacher':
        return jsonify({'error': 'No autorizado'}), 403

    data = request.get_json()
    attendance_id = data.get('attendance_id')
    new_status = data.get('new_status')
    student_code = data.get('student_code')

    if not new_status:
        return jsonify({'error': 'Falta new_status'}), 400

    allowed_status = ['on_time', 'late', 'absent', 'outside_campus']
    if new_status not in allowed_status:
        return jsonify({'error': 'Estado inválido'}), 400

    if attendance_id:
        att = Attendance.query.get(attendance_id)
        if not att:
            return jsonify({'error': 'Registro de asistencia no encontrado'}), 404

        att.status = new_status
        db.session.commit()
        return jsonify({'message': 'Status actualizado'}), 200
    else:
        if not student_code:
            return jsonify({'error': 'Se requiere student_code si no hay attendance_id'}), 400

        st = Student.query.filter_by(student_code=student_code).first()
        if not st:
            return jsonify({'error': 'Estudiante no encontrado'}), 404

        now_utc = datetime.utcnow()
        new_att = Attendance(
            student_id=st.id,
            course='Manual Correction',
            latitude=0.0,
            longitude=0.0,
            status=new_status,
            timestamp=now_utc
        )
        db.session.add(new_att)
        db.session.commit()
        return jsonify({'message': 'Nuevo registro creado con el status indicado'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    debug_mode = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=debug_mode)
