import os
import uuid
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

# Firebase SDK
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

# ---------- Helper ----------
def compute_stats():
    """ดึงตัวเลขสรุปจาก Firestore แบบง่ายและปลอดภัย"""
    try:
        total_users    = sum(1 for _ in db.collection('users').stream())
        total_notes    = sum(1 for _ in db.collection('notes').stream())
        total_reports  = sum(1 for _ in db.collection('reports').stream())
        total_comments = sum(1 for _ in db.collection('comments').stream())
        return {
            'total_users': total_users,
            'total_notes': total_notes,
            'total_reports': total_reports,
            'total_comments': total_comments
        }
    except Exception:
        return {
            'total_users': 0,
            'total_notes': 0,
            'total_reports': 0,
            'total_comments': 0
        }

# --- 3. Routes ---

@app.route('/')
def home():
    if 'student_id' in session:
        return redirect(url_for('dashboard'))
    elif session.get('admin'):
        return redirect(url_for('dashboard_admin'))
    return redirect(url_for('login'))

# 🔹 Login (User)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id']
        password = request.form['password']

        if '@' in login_id:
            email = login_id
        else:
            email = f"{login_id}@kmitl.ac.th"

        payload = {"email": email, "password": password, "returnSecureToken": True}

        resp = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json=payload
        )

        if resp.status_code == 200:
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

# 🔹 Register
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

# 🔹 Dashboard (โชว์โน้ตของทุกคน)
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    search_query = request.args.get('q', '').strip().lower()
    selected_category = request.args.get('category', '').strip()

    notes_ref = db.collection('notes').stream()
    notes = []

    for doc in notes_ref:
        n = doc.to_dict()
        n['note_id'] = doc.id
        n['title'] = n.get('title', '')
        n['subject'] = n.get('subject', '')
        n['faculty'] = n.get('faculty', '')
        n['fullname'] = n.get('fullname', '')
        n['like_count'] = n.get('like_count', 0)
        n['liked_by'] = n.get('liked_by', [])

        match_text = (
            search_query in n['title'].lower() or
            search_query in n['subject'].lower() or
            search_query in n['fullname'].lower()
        ) if search_query else True

        match_category = (selected_category == '' or selected_category == n['faculty'])

        if match_text and match_category:
            notes.append(n)

    categories = ["เทคโนโลยีคอมพิวเตอร์", "อิเล็กทรอนิกส์", "โทรคมนาคม"]

    return render_template('dashboard.html',
                           fullname=fullname,
                           notes=notes,
                           categories=categories,
                           library_mode=False,
                           favorite_mode=False,
                           q=search_query,
                           cat=selected_category)

# 🔹 Library (โน้ตของตนเอง)
@app.route('/library')
def library():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    fullname = session.get('fullname')
    notes_ref = db.collection('notes').where('uploader', '==', session['student_id']).stream()
    notes = [n.to_dict() for n in notes_ref]

    categories = ["เทคโนโลยีคอมพิวเตอร์", "อิเล็กทรอนิกส์", "โทรคมนาคม"]
    return render_template('dashboard.html',
                           fullname=fullname,
                           notes=notes,
                           categories=categories,
                           library_mode=True)

# 🔹 Favorite Notes
@app.route('/favorites')
def favorites():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    student_id = session['student_id']
    fullname = session.get('fullname')

    notes_ref = db.collection('notes').where('liked_by', 'array_contains', student_id).stream()
    notes = [doc.to_dict() for doc in notes_ref]

    return render_template('dashboard.html',
                           fullname=fullname,
                           notes=notes,
                           categories=[],
                           library_mode=False,
                           favorite_mode=True)

# 🔹 Create Note
@app.route('/create-note', methods=['GET', 'POST'])
def create_note():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))

    categories = ["เทคโนโลยีคอมพิวเตอร์", "อิเล็กทรอนิกส์", "โทรคมนาคม"]

    if request.method == 'GET':
        return render_template('create_note.html', categories=categories)

    try:
        note_id = str(uuid.uuid4())
        title = request.form.get('title', '')
        subject = request.form.get('subject', '')
        faculty = request.form.get('faculty', '')
        content = request.form.get('content', '')

        db.collection('notes').document(note_id).set({
            'note_id': note_id,
            'title': title,
            'subject': subject,
            'faculty': faculty,
            'content': content,
            'uploader': session['student_id'],
            'fullname': session.get('fullname', ''),
            'like_count': 0,
            'liked_by': [],
        })

        flash('✅ บันทึกโน้ตสำเร็จ!', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {e}', 'danger')
        return redirect(request.url)

# 🔹 Note Detail
@app.route('/note/<note_id>')
def note_detail(note_id):
    note_ref = db.collection('notes').document(note_id).get()
    if not note_ref.exists:
        flash('ไม่พบโน้ตที่ต้องการ', 'warning')
        return redirect(url_for('dashboard'))

    note = note_ref.to_dict()
    comments_ref = db.collection('comments').where('note_id', '==', note_id).stream()
    comments = [c.to_dict() for c in comments_ref]

    return render_template('note_detail.html', note=note, comments=comments)

# 🔹 Like / Unlike
@app.route('/toggle-like/<note_id>', methods=['POST'])
def toggle_like(note_id):
    if 'student_id' not in session:
        return jsonify({"success": False, "msg": "ไม่พบผู้ใช้"})

    note_ref = db.collection('notes').document(note_id)
    note = note_ref.get().to_dict()
    student_id = session['student_id']

    liked_by = note.get('liked_by', [])
    if student_id in liked_by:
        liked_by.remove(student_id)
    else:
        liked_by.append(student_id)

    note_ref.update({
        'liked_by': liked_by,
        'like_count': len(liked_by)
    })

    return jsonify({"success": True, "liked": student_id in liked_by, "like_count": len(liked_by)})

# 🔹 Comment
@app.route('/add-comment/<note_id>', methods=['POST'])
def add_comment(note_id):
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบ', 'danger')
        return redirect(url_for('login'))

    content = request.form.get('content', '').strip()
    if not content:
        flash('กรุณากรอกข้อความ', 'warning')
        return redirect(url_for('note_detail', note_id=note_id))

    comment_id = str(uuid.uuid4())
    db.collection('comments').document(comment_id).set({
        'comment_id': comment_id,
        'note_id': note_id,
        'content': content,
        'fullname': session.get('fullname', ''),
        'student_id': session['student_id'],
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    flash('เพิ่มคอมเมนต์เรียบร้อย', 'success')
    return redirect(url_for('note_detail', note_id=note_id))

# 🔹 Report Note
@app.route('/report-note/<note_id>', methods=['POST'])
def report_note(note_id):
    reason = request.form.get('reason', '')
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบ', 'danger')
        return redirect(url_for('login'))

    report_id = str(uuid.uuid4())
    db.collection('reports').document(report_id).set({
        'report_id': report_id,
        'note_id': note_id,
        'reason': reason,
        'reporter': session['student_id'],
        'fullname': session.get('fullname', ''),
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    flash('รายงานถูกส่งเรียบร้อยแล้ว', 'success')
    return redirect(url_for('note_detail', note_id=note_id))

# 🔹 Delete Note
@app.route('/delete-note/<note_id>', methods=['POST'])
def delete_note(note_id):
    db.collection('notes').document(note_id).delete()
    flash('ลบโน้ตเรียบร้อยแล้ว', 'info')
    return redirect(url_for('dashboard'))

# 🔹 Logout (User)
@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))

# 🔹 หน้า Login สำหรับแอดมิน
@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    ADMIN_EMAIL = "admin@neednote.com"
    ADMIN_PASSWORD = "123456"

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin'] = True
            flash('เข้าสู่ระบบผู้ดูแลระบบสำเร็จ!', 'success')
            return redirect(url_for('dashboard_admin'))  # ✅ เด้งแน่นอน
        else:
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template('login_admin.html')

# 🔹 Dashboard Admin
@app.route('/dashboard_admin')
def dashboard_admin():
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))

    try:
        stats = compute_stats()
        return render_template('dashboard_admin.html', stats=stats)
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการดึงข้อมูล: {e}', 'danger')
        return redirect(url_for('login_admin'))

# 🔹 Logout Admin
@app.route('/logout_admin')
def logout_admin():
    session.pop('admin', None)
    flash('ออกจากระบบผู้ดูแลแล้ว', 'info')
    return redirect(url_for('login_admin'))

# 🔹 ดูรายละเอียดแต่ละหมวดในแดชบอร์ดแอดมิน
@app.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))
    users = [u.to_dict() for u in db.collection('users').stream()]
    return render_template('admin_users.html', users=users)

@app.route('/admin/notes')
def admin_notes():
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))
    notes = [n.to_dict() for n in db.collection('notes').stream()]
    return render_template('admin_notes.html', notes=notes)

    return render_template('admin_comments.html', comments=comments)
@app.route('/admin/reports')
def admin_reports():
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))
    reports = [r.to_dict() for r in db.collection('reports').stream()]
    return render_template('admin_reports.html', reports=reports)

# 🔹 ฟังก์ชันแสดงคอมเมนต์ (แก้ใหม่ให้ดึงชื่อเรื่องโน้ต)
@app.route('/admin/comments')
def admin_comments():
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))

    comments = []
    for c in db.collection('comments').stream():
        comment = c.to_dict()
        note_ref = db.collection('notes').document(comment['note_id']).get()

        if note_ref.exists:
            note_data = note_ref.to_dict()
            comment['note_title'] = note_data.get('title', 'ไม่พบชื่อเรื่อง')
        else:
            comment['note_title'] = 'ไม่พบโน้ต'

        comment['comment_id'] = c.id
        comments.append(comment)

    # ✅ ต้องมี return แบบนี้
    return render_template('admin_comments.html', comments=comments)


# 🔹 ลบคอมเมนต์
@app.route('/admin/delete_comment/<comment_id>', methods=['POST'])
def admin_delete_comment(comment_id):
    if not session.get('admin'):
        flash('กรุณาเข้าสู่ระบบก่อน', 'warning')
        return redirect(url_for('login_admin'))

    try:
        db.collection('comments').document(comment_id).delete()
        flash('ลบคอมเมนต์เรียบร้อยแล้ว', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการลบ: {e}', 'danger')

    return redirect(url_for('admin_comments'))


# --- 4. Run App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
