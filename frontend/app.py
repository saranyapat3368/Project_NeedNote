import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, auth, firestore

# -------------------------------------------------
# 🔧 ตั้งค่า Flask
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------------------------------------
# 🔥 ตั้งค่า Firebase
# -------------------------------------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

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
        users_ref = db.collection("users").where("email", "==", username).stream()
        user = None
        for u in users_ref:
            user = u
            break

        if user:
            # หมายเหตุ: ในโปรเจกต์จริงควรใช้ Firebase Client SDK เพื่อตรวจรหัสผ่าน
            # ที่นี่จำลอง login ง่าย ๆ
            session['username'] = username
            session['uid'] = user.id
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

    notes_ref = db.collection("notes").where("user_id", "==", session['uid']).stream()
    notes = [{"title": n.get("title"), "filename": n.get("filename")} for n in notes_ref]
    return render_template('my_note.html', notes=notes)

# --------------------------------
# ✍️ สร้างโน้ตใหม่
# --------------------------------
@app.route('/create_note', methods=['GET', 'POST'])
def create_note():
    if 'uid' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        file = request.files.get('file')

        if not title:
            flash("Title is required")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # ✅ บันทึกข้อมูลลง Firestore
            db.collection("notes").add({
                "user_id": session['uid'],
                "title": title,
                "filename": filename
            })

            flash("Note created successfully!")
            return redirect(url_for('mynote'))
        else:
            flash("Invalid file or no file uploaded")

    return render_template('create_note.html')


if __name__ == '__main__':
    app.run(debug=True)
