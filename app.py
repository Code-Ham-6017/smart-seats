from flask import Flask, render_template, request, redirect, url_for, send_file, session
from database import init_db, save_seat_history, get_all_history, get_history_by_id, init_user_db, register_user, login_user, get_all_student_lists, save_student_list
from seat_logic import shuffle_seats
import json
import os
import qrcode
import random
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from database import register_user, get_user_info

app = Flask(__name__, 
            template_folder=os.path.abspath('templates'),
            static_folder=os.path.abspath('static'))
app.secret_key = "super_secret_key_for_seating_system" # 세션용 암호화 키

# 시스템 DB 및 유저 DB 동시 초기화
init_db()
init_user_db()

def create_pdf(seats, seat_id):
    os.makedirs("pdf", exist_ok=True)
    pdf_path = f"pdf/seats_{seat_id}.pdf"
    doc = SimpleDocTemplate(pdf_path)
    
    # 🎨 [핵심 수정] 윈도우 기본 한글 폰트(맑은 고딕)를 ReportLab에 등록합니다.
    try:
        # 윈도우 폰트 디렉토리에서 맑은 고딕(malgun.ttf)을 가져옵니다.
        font_path = "C:\\Windows\\Fonts\\malgun.ttf"
        pdfmetrics.registerFont(TTFont('MalgunGothic', font_path))
        font_name = 'MalgunGothic'
    except Exception as e:
        print(f"한글 폰트 로드 실패: {e}. 기본 폰트를 사용합니다.")
        font_name = 'Helvetica' # 폰트가 없을 경우의 대비책
        
    clean_seats = [[student if student else "" for student in row] for row in seats]
    table = Table(clean_seats)
    
    # 📝 테이블 스타일에 ('FONTNAME', (0,0), (-1,-1), font_name) 추가하여 한글을 입힙니다.
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), font_name), # 🔥 한글 폰트 지정
        ('FONTSIZE', (0,0), (-1,-1), 12),        # 글자 크기 조정
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    doc.build([Spacer(1, 20), table])
    return pdf_path

# 🔒 [로그인 상태 진단 함수 - 완벽 교정]
def get_current_user():
    # user_id 대신 확실하게 들어있는 username이 세션에 있는지 확인합니다.
    if "username" in session:
        return {
            "username": session["username"], 
            "role": session.get("role", "teacher"),
            "school": session.get("school", "미지정학교"),
            "grade": session.get("grade", "0"),
            "class_num": session.get("class_num", "0")
        }
    return None
# 인증 폼 화면
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        import sqlite3
        conn = sqlite3.connect("history.db")
        # 💡 데이터를 딕셔너리 형태로 편리하게 꺼내오기 위한 설정
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 가입된 유저가 있는지 아이디로 먼저 조회합니다.
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        # 유저가 존재하고, 비밀번호가 일치하는지 확인
        if user and user['password'] == password:
            # 🌟 [핵심] 로그인 세션에 유저의 모든 학급 메타데이터를 저장합니다.
            session['username'] = user['username']
            session['role'] = user['role']
            session['school'] = user['school'] if user['school'] else '미지정학교'
            session['grade'] = user['grade'] if user['grade'] else '0'
            session['class_num'] = user['class_num'] if user['class_num'] else '0'
            
            # 로그인 성공 후 메인 화면으로 리다이렉트
            return redirect('/')
        else:
            # 일치하지 않으면 경고창을 띄우고 이전 페이지로 돌려보냅니다.
            return "<script>alert('아이디 또는 비밀번호가 틀렸습니다.'); history.back();</script>"
            
    return render_template('login.html')
# ✨ [유일한 메인 홈 라우터] 중복 제거 및 명단 연동 완료!
@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')
        
    school = session.get('school', '미지정학교')
    grade = session.get('grade', '0')
    class_num = session.get('class_num', '0')
    
    # 🌟 [수정] HTML에서 {{ user.username }} 구조를 쓰고 있으므로, user 변수를 만들어서 함께 넘겨줍니다.
    user_info = {
        'username': session.get('username')
    }
    
    return render_template('index.html', 
                           school=school, 
                           grade=grade, 
                           class_num=class_num, 
                           user=user_info)  # <- 여기에 user를 추가!

# 과거 목록 조회
@app.route("/history")
def history():
    user = get_current_user()
    if not user: return redirect(url_for("login"))
    
    # 상단바 템플릿 대응용 구조 통일
    user_info = {'username': user['username']}
    
    try:
        records = get_all_history()
    except Exception as e:
        print(f"❌ 과거 기록 조회 중 DB 에러: {e}")
        return f"데이터베이스 조회 에러: {e}. 데이터베이스 파일(history.db)을 새로 고쳤다면 과거 기록 테이블 구조도 초기화해야 합니다.", 500
        
    return render_template("history.html", records=records, user=user_info)

@app.route("/delete_multiple", methods=["POST"])
def delete_multiple():
    user = get_current_user()
    if not user or user["role"] != "teacher": return "권한 없음", 403
    selected_ids = request.form.getlist("record_ids")
    if selected_ids:
        import sqlite3  # 안전하게 내부 임포트
        conn = sqlite3.connect("history.db")
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM seat_history WHERE id IN ({','.join('?' for _ in selected_ids)})", tuple(selected_ids))
        conn.commit(); conn.close()
    return redirect(url_for("history"))

@app.route("/delete_all", methods=["POST"])
def delete_all():
    user = get_current_user()
    if not user or user["role"] != "teacher": return "권한 없음", 403
    import sqlite3  # 안전하게 내부 임포트
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM seat_history")
    conn.commit(); conn.close()
    return redirect(url_for("history"))

# 🌟 [수정] uuid 문자열을 인식할 수 있도록 <int:>를 제거했습니다.
@app.route("/pdf/<seat_id>")
def download_pdf(seat_id):
    if not get_current_user(): return redirect(url_for("login"))
    import json
    from flask import send_file
    
    record = get_history_by_id(seat_id)
    if not record: return "기록 없음", 404
    
    # 💡 database.py의 컬럼명 규격에 맞게 꺼내오기 (seats 또는 seat_data)
    seats_json = record["seats"] if "seats" in record.keys() else record["seat_data"]
    
    return send_file(create_pdf(json.loads(seats_json), seat_id), as_attachment=True, download_name=f"seats_{seat_id}.pdf")
# --- 📝 명단 관리 전용 라우터 2개 ---
@app.route("/students")
def students_management():
    # 🌟 [교정] 로그인 세션에 username이 없거나 role이 'teacher'가 아니면 거부합니다.
    if 'username' not in session or session.get('role') != 'teacher':
        return "권한 없음 (교사 계정으로 로그인해 주세요)", 403
        
    classes = get_all_student_lists()
    
    # 상단 바에 'OOO님 로그인 중'을 띄워주기 위해 user 딕셔너리를 만들어서 넘겨줍니다.
    user_info = {'username': session.get('username')}
    
    return render_template("students.html", classes=classes, user=user_info)


@app.route("/students/save", methods=["POST"])
def students_save():
    # 🌟 [교정] 저장할 때도 로그인 세션을 기준으로 교사 권한을 확실하게 체크합니다.
    if 'username' not in session or session.get('role') != 'teacher':
        return "권한 없음", 403
        
    class_name = request.form["class_name"].strip()
    male_students = request.form["male_students"]
    female_students = request.form["female_students"]
    
    if save_student_list(class_name, male_students, female_students):
        return redirect(url_for("students_management"))
    return "명단 저장 실패", 500

@app.route('/logout')
def logout():
    # 세션에 저장된 교사 정보(아이디, 학교, 학년, 반)를 모두 깨끗하게 비웁니다.
    session.clear()
    # 로그아웃 후 로그인 페이지로 안전하게 리다이렉트(이동) 시킵니다.
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        school = request.form.get('school', '').strip()
        grade = request.form.get('grade', '').strip()
        class_num = request.form.get('class_num', '').strip()
        
        # database.py에 만들어둔 회원가입 함수를 호출합니다.
        from database import register_user
        if register_user(username, password, school, grade, class_num):
            return "<script>alert('회원가입 성공! 로그인해 주세요.'); location.href='/login';</script>"
        else:
            return "<script>alert('이미 존재하는 아이디입니다.'); history.back();</script>"
            
    # GET 요청일 때는 가입 페이지(HTML)를 보여줍니다.
    return render_template('register.html')

@app.route('/generate', methods=['POST'])
def generate():
    # 1. 로그인한 교사의 세션에서 학교, 학년, 반 정보를 자동으로 가져옵니다.
    school = session.get('school', '미지정학교')
    grade = session.get('grade', '0')
    class_num = session.get('class_num', '0')

    # 2. 화면에서 넘어온 기본 데이터 받기
    pair_mode = request.form.get('pair_mode', 'none')
    rows = int(request.form.get('rows', 5))
    cols = int(request.form.get('cols', 5))
    
    male_input = request.form.get('male_students', '')
    female_input = request.form.get('female_students', '')
    fixed_input = request.form.get('fixed_seats', '')
    
    # 3. 복도로 지정된 격자 좌표들 정리
    disabled_seats_raw = request.form.get('disabled_seats', '')
    disabled_seats_list = []
    if disabled_seats_raw:
        for coord in disabled_seats_raw.split('|'):
            if ',' in coord:
                r, c = coord.split(',')
                disabled_seats_list.append((int(r) - 1, int(c) - 1))

    # 4. 학생 명단 줄바꿈 기준으로 깔끔하게 리스트로 정리
    male_students = [s.strip() for s in male_input.split('\n') if s.strip()]
    female_students = [s.strip() for s in female_input.split('\n') if s.strip()]

    # 5. 고정석 데이터 파싱 (이름:행,열)
    fixed_seats_dict = {}
    if fixed_input.strip():
        for item in fixed_input.split('\n'):
            if ':' in item and ',' in item:
                try:
                    name, coord = item.split(':')
                    r, c = coord.split(',')
                    fixed_seats_dict[name.strip()] = (int(r) - 1, int(c) - 1)
                except ValueError:
                    continue

    # 6. seat_logic.py의 shuffle_seats 함수 작동시키기
    # (💡 프로젝트 구조에 맞춰 상단에 from seat_logic import shuffle_seats 가 있어야 합니다)
    try:
        from seat_logic import shuffle_seats
        seats = shuffle_seats(
            male_students, 
            female_students, 
            rows, 
            cols, 
            pair_mode, 
            fixed_seats_dict, 
            disabled_seats_list
        )
    except Exception as e:
        print(f"❌ 배정 로직 수행 중 에러 발생: {e}")
        return f"배정 로직 에러: {e}", 500

    # 7. 데이터베이스 저장 및 QR 코드 연동 로직
    try:
        import uuid
        import qrcode
        import os
        from database import save_seat_history

        # 고유 ID 생성
        seat_id = str(uuid.uuid4())[:8]
        teacher_id = session.get('username', 'guest')

        # database.py의 인자 순서와 100% 매칭하여 데이터 저장
        save_seat_history(seat_id, teacher_id, school, grade, class_num, seats)
        
        # QR 코드 파일 생성 및 저장
        qr_filename = f"qr_{seat_id}.png"
        qr_path = os.path.join('static', qr_filename)
        
        base_url = request.host_url
        qr_data = f"{base_url}view/{seat_id}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)
        
    except Exception as e:
        print(f"❌ DB 저장 또는 QR 생성 중 에러 발생: {e}")
        return f"시스템 저장 에러: {e}", 500

    # 8. 완성된 결과를 들고 결과창(result.html) 열어주기
    return render_template('result.html', seats=seats, seat_id=seat_id, qr_filename=qr_filename)

if __name__ == "__main__":
    # 🌟 [강제 테이블 생성 장치] 서버가 켜질 때 테이블을 무조건 직접 만듭니다.
    import sqlite3
    try:
        conn = sqlite3.connect("history.db")
        cursor = conn.cursor()
        
        # 1. 과거 배정 기록 테이블 강제 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seat_history (
                id TEXT PRIMARY KEY,
                teacher_id TEXT,
                school TEXT,
                grade TEXT,
                class_num TEXT,
                seats TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. 회원가입 유저 테이블 강제 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                school TEXT,
                grade TEXT,
                class_num TEXT,
                role TEXT DEFAULT 'teacher'
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ [성공] seat_history 및 users 테이블 강제 생성 완료!")
        
    except Exception as e:
        print(f"❌ DB 강제 생성 중 에러 발생: {e}")
    
    # 서버 실행
    app.run(debug=True, port=5000)