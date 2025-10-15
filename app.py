import os
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename

# Firebase SDK
import firebase_admin
from firebase_admin import credentials, auth, firestore

# --- 1. การตั้งค่าเบื้องต้น ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a-super-secret-key-for-sessions'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 2. เชื่อม Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 👉 Firebase Web API Key
FIREBASE_API_KEY = "AIzaSyAm3ZezqVvpsk40Z_ggc1L_0dzkxE4Sm1Q"

# --- 3. ฟังก์ชันช่วยเหลือ ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- 4. Routes ---
@app.route('/')
def home():
    """หน้าแรก: ถ้า login แล้วให้ไป Dashboard ถ้ายังให้ไป Login"""
    if 'student_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# 🔹 หน้า Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id']
        password = request.form['password']

        # ตรวจว่าเป็นอีเมลหรือรหัสนักศึกษา
        if '@' in login_id:
            email = login_id
        else:
            email = f"{login_id}@kmitl.ac.th"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        # 🔍 ยิง API ไปที่ Firebase Authentication
        resp = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json=payload
        )

        if resp.status_code == 200:
            # ✅ Login สำเร็จ (Firebase Auth)
            data = resp.json()
            print("✅ Login success from Firebase:", data)

            # 🔍 ดึงข้อมูลผู้ใช้จาก Firestore
            docs = db.collection('users').where('email', '==', email).stream()
            user_doc = None
            for d in docs:
                user_doc = d.to_dict()
                print("🎯 Found user in Firestore:", user_doc)

            if user_doc:
                session['student_id'] = user_doc['student_id']
                session['fullname'] = user_doc['fullname']
                flash('เข้าสู่ระบบสำเร็จ!', 'success')
                print("📦 Session set:", dict(session))
                return redirect(url_for('dashboard'))
            else:
                flash('ไม่พบข้อมูลผู้ใช้ใน Firestore โปรดลงทะเบียนก่อน', 'danger')
                print("⚠️ User not found in Firestore for:", email)
                return redirect(url_for('register'))

        else:
            print("❌ Firebase login failed:", resp.text)
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template('login.html')


# 🔹 หน้า Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        student_id = request.form['student_id']
        email = request.form['email']
        password = request.form['password']

        if not email.endswith('@kmitl.ac.th'):
            flash('กรุณาใช้อีเมลของสถาบัน (@kmitl.ac.th)', 'danger')
            return redirect(url_for('register'))

        try:
            existing_student = db.collection('users').document(student_id).get()
            if existing_student.exists:
                flash('รหัสนักศึกษานี้ถูกใช้แล้ว', 'warning')
                return redirect(url_for('register'))

            existing_email = db.collection('users').where('email', '==', email).stream()
            if any(existing_email):
                flash('อีเมลนี้ถูกใช้งานแล้ว', 'warning')
                return redirect(url_for('register'))

            # สร้างผู้ใช้ใน Firebase Auth
            auth.create_user(
                uid=student_id,
                email=email,
                password=password,
                display_name=fullname
            )

            # เก็บข้อมูลใน Firestore
            db.collection('users').document(student_id).set({
                'fullname': fullname,
                'student_id': student_id,
                'email': email,
                'role': 'user'
            })

            flash('✅ ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'เกิดข้อผิดพลาด: {e}', 'danger')

    return render_template('register.html')


# 🔹 หน้า Dashboard
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    print("🧑‍💻 Dashboard loaded for:", fullname)
    return render_template('dashboard.html', fullname=fullname, library_mode=False)


# 🔹 หน้า Library (แก้ error url_for)
@app.route('/library')
def library():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    print("📚 Library loaded for:", fullname)
    # ใช้ dashboard.html เดิม แต่อยู่ในโหมดคลังโน้ต
    return render_template('dashboard.html', fullname=fullname, library_mode=True)


# 🔹 หน้า Create Note
@app.route('/create-note')
def create_note():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))
    return "<h3>หน้านี้คือ Create Note (ยังไม่ได้ทำระบบอัปโหลด)</h3>"


# 🔹 Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))


# --- 5. Run app ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
