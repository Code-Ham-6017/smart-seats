import sqlite3
import json

def init_db():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seat_data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def init_user_db():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    # 💡 username의 UNIQUE 제약조건을 제거하여 동일 아이디 가입이 가능하도록 수정합니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    # 📝 학생 명단 관리를 위한 새로운 테이블 추가 (반 이름, 남학생 명단, 여학생 명단)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL,
            male_students TEXT,
            female_students TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_seat_history(seats):
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    seat_json = json.dumps(seats, ensure_ascii=False)
    cursor.execute("INSERT INTO seat_history (seat_data) VALUES (?)", (seat_json,))
    seat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return seat_id

def get_all_history():
    conn = sqlite3.connect("history.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at FROM seat_history ORDER BY id DESC")
    records = cursor.fetchall()
    conn.close()
    return records

def get_history_by_id(seat_id):
    conn = sqlite3.connect("history.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seat_history WHERE id = ?", (seat_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def register_user(username, password, role):
    conn = sqlite3.connect("history.db")
    try:
        cursor = conn.cursor()
        # 동일 아이디가 있어도 무조건 INSERT 됩니다.
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        return True
    except Exception as e:
        print(f"회원가입 오류: {e}")
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect("history.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # 동일 아이디가 있을 경우, 가장 최근에 가입한 계정으로 로그인되도록 세팅
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ? ORDER BY id DESC", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

# --- 📝 학생 명단 관리용 신규 함수들 ---
def save_student_list(class_name, male_text, female_text):
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO student_lists (class_name, male_students, female_students)
            VALUES (?, ?, ?)
            ON CONFLICT(class_name) DO UPDATE SET
            male_students=excluded.male_students,
            female_students=excluded.female_students
        """, (class_name, male_text, female_text))
        conn.commit()
        return True
    except Exception as e:
        print(f"명단 저장 오류: {e}")
        return False
    finally:
        conn.close()

def get_all_student_lists():
    conn = sqlite3.connect("history.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_lists ORDER BY class_name ASC")
    lists = cursor.fetchall()
    conn.close()
    return lists