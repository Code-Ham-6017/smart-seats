import sqlite3
import json

def init_db():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    # 🏫 자리 배치 이력에 학교, 학년, 반, 생성한 교사 ID(username) 필드를 추가합니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seat_history (
            id TEXT PRIMARY KEY,
            username TEXT,
            school TEXT,
            grade TEXT,
            class_num TEXT,
            seat_data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def init_user_db():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    # 🏫 회원가입 테이블(users)에 가입 시 선택한 학교, 학년, 반 필드를 추가합니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            school TEXT,
            grade TEXT,
            class_num TEXT
        )
    """)
    # 학생 명단 관리 테이블 (기존 유지)
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

import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # 학교, 학년, 반 필드(Column)를 추가하여 테이블을 생성합니다.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seat_history (
            id TEXT PRIMARY KEY,
            teacher_id TEXT,
            school TEXT,
            grade TEXT,
            class_num TEXT,
            seats_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_seat_history(seat_id, teacher_id, school, grade, class_num, seats_data):
    import json
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # 3개에서 5개의 메타데이터를 저장하도록 확장
    cursor.execute(
        "INSERT INTO seat_history (id, teacher_id, school, grade, class_num, seats_data) VALUES (?, ?, ?, ?, ?, ?)",
        (seat_id, teacher_id, school, grade, class_num, json.dumps(seats_data, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

# 우리 반의 과거 배정 이력만 쏙 골라서 가져오는 함수 추가
def get_class_history(school, grade, class_num):
    import json
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, teacher_id, seats_data, created_at FROM seat_history WHERE school = ? AND grade = ? AND class_num = ? ORDER BY created_at DESC",
        (school, grade, class_num)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'id': row[0],
            'teacher_id': row[1],
            'seats': json.loads(row[2]),
            'created_at': row[3]
        })
    return history

# 📝 회원가입 처리 함수 (기존 role과 새로운 학급 정보를 함께 저장)
def register_user(username, password, school, grade, class_num):
    import sqlite3
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    try:
        # role 자리에 'teacher'를 명확하게 꽂아줍니다.
        cursor.execute(
            "INSERT INTO users (username, password, role, school, grade, class_num) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password, 'teacher', school, grade, class_num)
        )
        conn.commit()
        success = True
    except Exception as e:
        print(f"❌ 회원가입 DB 저장 에러: {e}")
        success = False
    conn.close()
    return success

# 🔍 [에러 원인!] 로그인 성공 시 유저의 학급 정보를 한꺼번에 세션에 담기 위해 가져오는 함수
def get_user_info(username):
    import sqlite3
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, school, grade, class_num FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'username': row[0], 'school': row[1], 'grade': row[2], 'class_num': row[3]}
    return None