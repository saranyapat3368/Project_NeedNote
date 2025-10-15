import os
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore

# --- 1. การตั้งค่าเบื้องต้น ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-for-sessions'

# --- 2. เชื่อม Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Firebase Web API Key
FIREBASE_API_KEY = "AIzaSyAm3ZezqVvpsk40Z_ggc1L_0dzkxE4Sm1Q"

# --- 3. Routes ---

# Home
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login นักศึกษา
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id']
        password = request.form['password']
        email = login_id if '@' in login_id else f"{login_id}@kmitl.ac.th"

        payload = {"email": email,"password": password,"returnSecureToken": True}
        resp = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json=payload
        )

        if resp.status_code == 200:
            docs = db.collection('users').where('email','==',email).stream()
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

# Register นักศึกษา
@app.route('/register', methods=['GET','POST'])
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

            existing_email = db.collection('users').where('email','==',email).stream()
            if any(existing_email):
                flash('อีเมลนี้ถูกใช้งานแล้ว', 'warning')
                return redirect(url_for('register'))

            auth.create_user(
                uid=student_id,
                email=email,
                password=password,
                display_name=fullname
            )

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

# Dashboard นักศึกษา
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    notes_ref = db.collection('notes').stream()
    notes = []
    for doc in notes_ref:
        n = doc.to_dict()
        n['id'] = doc.id
        n['like_count'] = n.get('like_count',0)
        n['liked_by'] = n.get('liked_by',[])
        notes.append(n)

    categories = ["เทคโนโลยีคอมพิวเตอร์","อิเล็กทรอนิกส์","โทรคมนาคม"]
    return render_template('dashboard.html', fullname=fullname, notes=notes, categories=categories, library_mode=False)

# Library โน้ตส่วนตัว
@app.route('/library')
def library():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    notes_ref = db.collection('notes').where('uploader','==', session['student_id']).stream()
    notes = []
    for doc in notes_ref:
        n = doc.to_dict()
        n['id'] = doc.id
        n['like_count'] = n.get('like_count',0)
        n['liked_by'] = n.get('liked_by',[])
        notes.append(n)

    categories = ["เทคโนโลยีคอมพิวเตอร์","อิเล็กทรอนิกส์","โทรคมนาคม"]
    return render_template('dashboard.html', fullname=fullname, notes=notes, categories=categories, library_mode=True)

# สร้างโน้ต
@app.route('/create-note', methods=['GET','POST'])
def create_note():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    categories = ["เทคโนโลยีคอมพิวเตอร์","อิเล็กทรอนิกส์","โทรคมนาคม"]

    if request.method == 'GET':
        return render_template('create_note.html', categories=categories)

    try:
        note_id = str(uuid.uuid4())
        title = request.form.get('title','')
        subject = request.form.get('subject','')
        faculty = request.form.get('faculty','')
        content = request.form.get('content','')

        db.collection('notes').document(note_id).set({
            'note_id': note_id,
            'title': title,
            'subject': subject,
            'faculty': faculty,
            'content': content,
            'uploader': session['student_id'],
            'fullname': session.get('fullname',''),
            'like_count':0,
            'liked_by':[],
            'views':0
        })

        flash('✅ บันทึกโน้ตสำเร็จ!', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {e}', 'danger')
        return redirect(request.url)

# Note Detail
@app.route('/note/<note_id>')
def note_detail(note_id):
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    try:
        note_doc = db.collection('notes').document(note_id).get()
        if not note_doc.exists:
            flash('ไม่พบโน้ตที่ต้องการ', 'warning')
            return redirect(url_for('dashboard'))

        note = note_doc.to_dict() or {}
        note['id'] = note_doc.id
        note['like_count'] = note.get('like_count',0)
        note['liked_by'] = note.get('liked_by',[])

        # ดึงคอมเมนต์
        comments = []
        try:
            comments_ref = db.collection('comments').where('note_id','==',note_id).stream()
            comments = [c.to_dict() for c in comments_ref]
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดในการดึงคอมเมนต์: {e}', 'warning')

        return render_template('note_detail.html', note=note, comments=comments)

    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการดึงโน้ต: {e}', 'danger')
        return redirect(url_for('dashboard'))

# Report Note
@app.route('/report-note/<note_id>', methods=['POST'])
def report_note(note_id):
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบ', 'danger')
        return redirect(url_for('login'))

    try:
        note_ref = db.collection('notes').document(note_id)
        note = note_ref.get()
        if not note.exists:
            flash('ไม่พบโน้ตที่ต้องการรายงาน', 'warning')
            return redirect(url_for('dashboard'))

        report_id = str(uuid.uuid4())
        db.collection('reports').document(report_id).set({
            'report_id': report_id,
            'note_id': note_id,
            'student_id': session['student_id'],
            'fullname': session.get('fullname',''),
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        flash('รายงานโน้ตเรียบร้อยแล้ว', 'success')
        return redirect(url_for('note_detail', note_id=note_id))

    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการรายงานโน้ต: {e}', 'danger')
        return redirect(url_for('note_detail', note_id=note_id))

# Toggle Like
@app.route('/toggle-like/<note_id>', methods=['POST'])
def toggle_like(note_id):
    if 'student_id' not in session:
        return jsonify({"success":False, "msg":"ไม่พบผู้ใช้"})

    note_ref = db.collection('notes').document(note_id)
    note = note_ref.get().to_dict() or {}
    student_id = session['student_id']

    liked_by = note.get('liked_by',[])
    if student_id in liked_by:
        liked_by.remove(student_id)
    else:
        liked_by.append(student_id)

    note_ref.update({
        'liked_by': liked_by,
        'like_count': len(liked_by)
    })

    return jsonify({"success":True, "liked": student_id in liked_by, "like_count": len(liked_by)})

# Add Comment
@app.route('/add-comment/<note_id>', methods=['POST'])
def add_comment(note_id):
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบ', 'danger')
        return redirect(url_for('login'))

    content = request.form.get('content','')
    if not content.strip():
        flash('กรุณากรอกข้อความ', 'warning')
        return redirect(url_for('note_detail', note_id=note_id))

    comment_id = str(uuid.uuid4())
    db.collection('comments').document(comment_id).set({
        'comment_id': comment_id,
        'note_id': note_id,
        'content': content,
        'fullname': session.get('fullname',''),
        'student_id': session['student_id'],
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    flash('เพิ่มคอมเมนต์เรียบร้อย', 'success')
    return redirect(url_for('note_detail', note_id=note_id))

# Delete Note
@app.route('/delete-note/<note_id>', methods=['POST'])
def delete_note(note_id):
    if 'student_id' not in session and 'admin' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    try:
        note_ref = db.collection('notes').document(note_id)
        note = note_ref.get()
        if not note.exists:
            flash('ไม่พบโน้ตที่ต้องการลบ', 'warning')
            return redirect(url_for('dashboard'))

        if session.get('student_id') == note.to_dict().get('uploader') or session.get('admin'):
            note_ref.delete()
            flash('ลบโน้ตเรียบร้อยแล้ว', 'success')
        else:
            flash('คุณไม่มีสิทธิ์ลบโน้ตนี้', 'danger')

    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการลบโน้ต: {e}', 'danger')

    if session.get('admin'):
        return redirect(url_for('dashboard_admin'))
    else:
        return redirect(url_for('dashboard'))

# Admin Login
@app.route('/login-admin', methods=['GET','POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form.get('admin_email')
        password = request.form.get('admin_password')

        if email == "admin@kmitl.ac.th" and password == "password123":
            session['admin'] = True
            flash('เข้าสู่ระบบแอดมินสำเร็จ!', 'success')
            return redirect(url_for('dashboard_admin'))
        else:
            flash('อีเมลหรือรหัสผ่านแอดมินไม่ถูกต้อง', 'danger')
            return redirect(url_for('login_admin'))

    return render_template('login_admin.html')

# Dashboard แอดมิน
@app.route('/dashboard-admin')
def dashboard_admin():
    if 'admin' not in session:
        flash('กรุณาเข้าสู่ระบบแอดมินก่อน', 'danger')
        return redirect(url_for('login_admin'))

    notes_ref = db.collection('notes').stream()
    notes = []
    total_views = 0
    for doc in notes_ref:
        n = doc.to_dict()
        n['id'] = doc.id
        n['like_count'] = n.get('like_count',0)
        notes.append(n)
        total_views += n.get('views',0)

    stats = {
        'total_notes': len(notes),
        'total_views': total_views,
        'total_users': len(list(db.collection('users').stream())),
        'logins_today': 0
    }

    return render_template('dashboard_admin.html', notes=notes, stats=stats)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
