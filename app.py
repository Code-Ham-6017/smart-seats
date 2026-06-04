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

app = Flask(__name__)
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

# 🔒 [로그인 상태 진단 함수]
def get_current_user():
    if "user_id" in session:
        return {"id": session["user_id"], "username": session["username"], "role": session["role"]}
    return None

# 인증 폼 화면
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = login_user(username, password)
        
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            
            current_role = str(user["role"]).strip().lower()
            
            if current_role == "teacher":
                return redirect(url_for("index"))  # 교사는 메인 입력창으로!
            else:
                return redirect(url_for("history"))  # 학생은 과거 기록 조회창으로!
                
        return render_template("login.html", error="아이디 또는 비밀번호가 틀렸습니다.")
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    if register_user(username, password, role):
        return render_template("login.html", error="회원가입 성공! 로그인해 주세요.")
    return render_template("login.html", error="이미 존재하는 아이디입니다.")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ✨ [유일한 메인 홈 라우터] 중복 제거 및 명단 연동 완료!
@app.route("/")
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] != "teacher":
        return "<h1>⚠️ 접근 권한이 없습니다. 교사 계정으로 로그인하세요.</h1><br><a href='/history'>과거 기록 가기</a>"
    
    classes = get_all_student_lists()
    return render_template("index.html", user=user, classes=classes)

@app.route('/generate', methods=['POST'])
def generate():
    # 1. 프론트엔드에서 넘어온 데이터 받기
    pair_mode = request.form.get('pair_mode', 'none')
    rows = int(request.form.get('rows', 5))
    cols = int(request.form.get('cols', 5))
    
    male_input = request.form.get('male_students', '')
    female_input = request.form.get('female_students', '')
    fixed_input = request.form.get('fixed_seats', '')
    
    # 💡 [핵심] 메인 화면 격자판에서 클릭한 복도(통로) 데이터 받아오기
    disabled_seats_raw = request.form.get('disabled_seats', '')
    disabled_seats_list = []
    if disabled_seats_raw:
        for coord in disabled_seats_raw.split('|'):
            if ',' in coord:
                r, c = coord.split(',')
                # 파이썬 리스트 인덱스는 0부터 시작하므로 입력값(1~N)에서 1을 빼줍니다.
                disabled_seats_list.append((int(r) - 1, int(c) - 1))

    # 2. 학생 명단 정리 (줄바꿈 기준 공백 제거)
    male_students = [s.strip() for s in male_input.split('\n') if s.strip()]
    female_students = [s.strip() for s in female_input.split('\n') if s.strip()]

    # 3. 고정석 데이터 파싱 (이름:행,열)
    fixed_seats_dict = {}
    if fixed_input.strip():
        for item in fixed_input.split('\n'):
            if ':' in item and ',' in item:
                try:
                    name, coord = item.split(':')
                    r, c = coord.split(',')
                    fixed_seats_dict[name.strip()] = (int(r) - 1, int(c) - 1)
                except ValueError:
                    continue # 잘못된 입력 형식은 무시

    # 4. 업데이트된 seat_logic의 shuffle_seats 함수 호출
    try:
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
        print(f"배정 로직 에러 발생: {e}")
        return f"자리 배정 중 오류가 발생했습니다: {e}", 500

    # 5. 데이터베이스 저장 및 QR 코드 생성 로직 (기존 코드 유지)
    # (선생님의 기존 app.py 코드에 맞게 seat_id와 qr_filename을 생성하고 리턴하는 부분입니다)
    # 예시:
    # seat_id = save_to_db(seats) 
    # qr_filename = generate_qr(seat_id)
    
    # 임시 테스트용 리턴 (기존의 실제 return 구문으로 유지하셔도 됩니다)
    import uuid
    dummy_id = str(uuid.uuid4()[:8])
    return render_template('result.html', seats=seats, seat_id=dummy_id, qr_filename="")
@app.route("/result/<int:seat_id>")
def result(seat_id):
    if not get_current_user(): return redirect(url_for("login"))
    record = get_history_by_id(seat_id)
    if not record: return "기록 없음", 404
    seats = json.loads(record["seat_data"])
    return render_template("result.html", seats=seats, seat_id=seat_id, qr_filename=f"qr_{seat_id}.png")

# 과거 목록 조회
@app.route("/history")
def history():
    user = get_current_user()
    if not user: return redirect(url_for("login"))
    records = get_all_history()
    return render_template("history.html", records=records, user=user)

@app.route("/delete_multiple", methods=["POST"])
def delete_multiple():
    user = get_current_user()
    if not user or user["role"] != "teacher": return "권한 없음", 403
    selected_ids = request.form.getlist("record_ids")
    if selected_ids:
        conn = sqlite3.connect("history.db")
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM seat_history WHERE id IN ({','.join('?' for _ in selected_ids)})", tuple(selected_ids))
        conn.commit(); conn.close()
    return redirect(url_for("history"))

@app.route("/delete_all", methods=["POST"])
def delete_all():
    user = get_current_user()
    if not user or user["role"] != "teacher": return "권한 없음", 403
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM seat_history")
    conn.commit(); conn.close()
    return redirect(url_for("history"))

@app.route("/pdf/<int:seat_id>")
def download_pdf(seat_id):
    if not get_current_user(): return redirect(url_for("login"))
    record = get_history_by_id(seat_id)
    if not record: return "기록 없음", 404
    return send_file(create_pdf(json.loads(record["seat_data"]), seat_id), as_attachment=True, download_name=f"seats_{seat_id}.pdf")

# --- 📝 명단 관리 전용 라우터 2개 ---
@app.route("/students")
def students_management():
    user = get_current_user()
    if not user or user["role"] != "teacher":
        return "권한 없음", 403
    classes = get_all_student_lists()
    return render_template("students.html", classes=classes)

@app.route("/students/save", methods=["POST"])
def students_save():
    user = get_current_user()
    if not user or user["role"] != "teacher":
        return "권한 없음", 403
    class_name = request.form["class_name"].strip()
    male_students = request.form["male_students"]
    female_students = request.form["female_students"]
    
    if save_student_list(class_name, male_students, female_students):
        return redirect(url_for("students_management"))
    return "명단 저장 실패", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)

    create_pdf