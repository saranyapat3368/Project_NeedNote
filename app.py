import os
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
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
            print("✅ Login success:", data)

            # 🔍 ดึงข้อมูลผู้ใช้จาก Firestore
            docs = db.collection('users').where('email', '==', email).stream()
            user_doc = None
            for d in docs:
                user_doc = d.to_dict()

            if user_doc:
                session['student_id'] = user_doc['student_id']
                session['fullname'] = user_doc['fullname']
                flash('เข้าสู่ระบบสำเร็จ!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('ไม่พบข้อมูลผู้ใช้ในระบบ โปรดลงทะเบียนก่อน', 'danger')
                return redirect(url_for('register'))
        else:
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
            # ตรวจสอบซ้ำ
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

    # ดึงโน้ตทั้งหมดจาก Firestore
    notes_ref = db.collection('notes').where('uploader', '==', session['student_id']).stream()
    notes = [doc.to_dict() for doc in notes_ref]

    categories = ["เทคโนโลยีคอมพิวเตอร์", "อิเล็กทรอนิกส์", "โทรคมนาคม"]

    return render_template('dashboard.html', fullname=fullname, notes=notes, categories=categories, library_mode=False)


# 🔹 หน้า Library (optional)
@app.route('/library')
def library():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    return render_template('dashboard.html', fullname=fullname, notes=[], library_mode=True)


# 🔹 หน้า Create Note
@app.route('/create-note', methods=['GET', 'POST'])
def create_note():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    categories = ["เทคโนโลยีคอมพิวเตอร์", "อิเล็กทรอนิกส์", "โทรคมนาคม"]

    if request.method == 'GET':
        return render_template('create_note.html', categories=categories)

    # POST: บันทึกไฟล์
    file = request.files.get('note_file')
    if not file or file.filename == '':
        flash('กรุณาเลือกไฟล์ก่อนอัปโหลด', 'danger')
        return redirect(request.url)

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        note_id = str(uuid.uuid4())
        db.collection('notes').document(note_id).set({
            'note_id': note_id,
            'title': request.form['title'],
            'subject': request.form['subject'],
            'faculty': request.form['faculty'],
            'filename': filename,
            'uploader': session['student_id'],
            'fullname': session.get('fullname', '')
        })

        flash('✅ อัปโหลดโน้ตสำเร็จ!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('ชนิดไฟล์ไม่ถูกต้อง', 'danger')
        return redirect(request.url)


# 🔹 หน้าอ่านรายละเอียดโน้ต
@app.route('/note/<note_id>')
def note_detail(note_id):
    note_ref = db.collection('notes').document(note_id).get()
    if not note_ref.exists:
        flash('ไม่พบโน้ตที่ต้องการ', 'warning')
        return redirect(url_for('dashboard'))
    note = note_ref.to_dict()
    return render_template('note_detail.html', note=note)


# 🔹 ลบโน้ต
@app.route('/delete-note/<note_id>', methods=['POST'])
def delete_note(note_id):
    db.collection('notes').document(note_id).delete()
    flash('ลบโน้ตเรียบร้อยแล้ว', 'info')
    return redirect(url_for('dashboard'))


# 🔹 ออกจากระบบ
@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))


# --- 5. Run App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)


