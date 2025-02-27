import psycopg2
import csv

DB_HOST = "dpg-cv0fcf8gph6c73casoh0-a.oregon-postgres.render.com"
DB_NAME = "asistencia_ia"
DB_USER = "asistencia_user"
DB_PASSWORD = "n7GZFVZzgE5QyEnP7V9fDgLPwMfYN5qZ"

CSV_FILE_PATH = "estudiantes.csv"

def main():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                insert_sql = """
                    INSERT INTO students (
                        student_code, email, paternal_surname, maternal_surname,
                        first_name, group_col, password, user_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """
                # Asumimos que el password es igual al código
                data = (
                    row['CODIGO'],
                    row['CORREO'],
                    row['APELLIDO PATERNO'],
                    row['APELLIDO MATERNO'],
                    row['NOMBRE'],
                    row['GRUPO'],
                    row['CODIGO'],
                    row['USER_TYPE']  # student o teacher
                )
                cur.execute(insert_sql, data)

        conn.commit()
        cur.close()
        conn.close()
        print("Estudiantes importados con éxito.")

    except Exception as e:
        print("Error importando estudiantes:", e)

if __name__ == "__main__":
    main()
