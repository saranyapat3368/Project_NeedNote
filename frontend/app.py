import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, auth, firestore

# -------------------------------------------------
# 🔧 ตั้งค่า Flask
# -------------------------------------------------
app = Flask(__name__)
# ⚠️ เปลี่ยน Secret Key ให้ปลอดภัย
app.secret_key = 'your_secret_key' 

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------------------------------------
# 🔥 ตั้งค่า Firebase
# -------------------------------------------------
# ⚠️ ตรวจสอบให้แน่ใจว่าไฟล์ serviceAccountKey.json อยู่ในไดเรกทอรีเดียวกันกับ app.py
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except FileNotFoundError:
    print("FATAL: serviceAccountKey.json not found. Firebase functionality will fail.")
    db = None 

# -------------------------------------------------
# 🧩 ฟังก์ชันช่วย
# -------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------------------------
# 🌐 Routes
# -------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

# --------------------------------
# 🔐 สมัครสมาชิก
# --------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        username = request.form['username']
        password = request.form['password']

        try:
            # ✅ สร้างผู้ใช้ใน Firebase Authentication
            user = auth.create_user(
                email=username,
                password=password,
                display_name=name
            )

            # ✅ เก็บข้อมูลเพิ่มเติมใน Firestore
            if db:
                db.collection("users").document(user.uid).set({
                    "name": name,
                    "student_id": student_id,
                    "email": username
                })

            flash("Register successful! Please login.")
            return redirect(url_for('login'))

        except Exception as e:
            flash(f"Error: {e}")
            return redirect(url_for('register'))

    return render_template('register.html')

# --------------------------------
# 🔑 เข้าสู่ระบบ
# --------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 🔥 ตรวจสอบผู้ใช้ใน Firestore
        user = None
        if db:
            users_ref = db.collection("users").where("email", "==", username).stream()
            for u in users_ref:
                user = u
                break

        if user:
            # หมายเหตุ: ในโปรเจกต์จริงควรใช้ Firebase Client SDK เพื่อตรวจรหัสผ่าน
            # ที่นี่จำลอง login ง่าย ๆ
            session['username'] = username
            session['uid'] = user.id
            flash("เข้าสู่ระบบสำเร็จ!")
            return redirect(url_for('mainnote'))
        else:
            flash("Login failed. Invalid email or password.")
            return redirect(url_for('login'))

    return render_template('login.html')

# --------------------------------
# 🚪 ออกจากระบบ
# --------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --------------------------------
# 📝 หน้าโน้ตหลัก
# --------------------------------
@app.route('/mainnote')
def mainnote():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('main_note.html', username=session['username'])

# --------------------------------
# 📘 คลังโน้ตของฉัน
# --------------------------------
@app.route('/mynote')
def mynote():
    if 'uid' not in session:
        return redirect(url_for('login'))

    notes = []
    if db:
        notes_ref = db.collection("notes").where("user_id", "==", session['uid']).stream()
        # ปรับปรุงการดึงข้อมูลเพื่อแสดงผลใน my_note.html
        notes = [{"title": n.get("subject_name"), "filename": n.get("filename"), "branch": n.get("department_branch"), "year": n.get("student_year")} for n in notes_ref]
        
    return render_template('my_note.html', notes=notes)

# --------------------------------
# ✍️ สร้างโน้ตใหม่ (ส่วนที่ปรับปรุง)
# --------------------------------
@app.route('/create_note', methods=['GET', 'POST'])
def create_note():
    if 'uid' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 💡 รับข้อมูลตามชื่อฟิลด์ใน HTML
        department_branch = request.form.get('department_branch')
        subject_name = request.form.get('subject_name')
        student_year = request.form.get('student_year')
        # 💡 รับไฟล์ตามชื่อ 'note_file' ใน HTML
        file = request.files.get('note_file') 

        # ตรวจสอบข้อมูลที่จำเป็น
        if not all([department_branch, subject_name, student_year]):
            flash("กรุณากรอกข้อมูลให้ครบทุกช่อง", 'error')
            return redirect(request.url)
        
        # ตรวจสอบและบันทึกไฟล์
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if db:
                try:
                    # บันทึกไฟล์ลงในโฟลเดอร์ 'uploads'
                    file.save(filepath)

                    # ✅ บันทึกข้อมูลลง Firestore พร้อมฟิลด์ใหม่ทั้งหมด
                    db.collection("notes").add({
                        "user_id": session['uid'],
                        "department_branch": department_branch,
                        "subject_name": subject_name,
                        "student_year": student_year,
                        "filename": filename,
                    })

                    flash("อัปโหลดโน้ตสำเร็จ!", 'success')
                    # Redirect ไปที่หน้าโน้ตของฉัน เพื่อให้ผู้ใช้เห็นโน้ตที่เพิ่งสร้าง
                    return redirect(url_for('mynote')) 

                except Exception as e:
                    flash(f"Error during file save or database write: {e}", 'error')
                    return redirect(request.url)
            else:
                 flash("ไม่สามารถเชื่อมต่อฐานข้อมูลได้", 'error')
                 return redirect(request.url)
                
        else:
            flash("กรุณาเลือกไฟล์ที่ถูกต้อง (.pdf, .png, .jpg, .jpeg) เพื่ออัปโหลด", 'error')
            return redirect(request.url)

    return render_template('create_note.html')


if __name__ == '__main__':
    app.run(debug=True)