import os, uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename

# -------- Config --------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a-super-secret-key-for-sessions'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------- In-memory data --------
users = {}     # {'sid': {'password': '...', 'fullname': '...'}}
notes = {}     # {'nid': {title, subject, faculty, filename, uploader, like_count, report_count, created_at}}
likes = {}     # {'sid': set([nid,...])}
comments = {}  # {'nid': [{id, user, text, created_at, report_count}, ...]}

CATEGORIES = [
    'เทคโนโลยีคอมพิวเตอร์',
    'อิเล็กทรอนิกส์และโทรคมนาคม',
    'เทคโนโลยีอิเล็กทรอนิกส์ (ต่อเนื่อง)',
]

# -------- Helpers --------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def require_login():
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return False
    return True

# ---------- inline preview & download by note_id ----------
def _get_note_or_404(note_id):
    """คืน (note, filepath) หรือ 404 ถ้าไม่พบ"""
    n = notes.get(note_id)
    if not n:
        abort(404)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], n['filename'])
    if not os.path.exists(filepath):
        abort(404)
    return n, filepath

@app.route('/inline/<note_id>')
def inline_file(note_id):
    """พรีวิวไฟล์ในกรอบ (PDF/PNG/JPG)"""
    n, _ = _get_note_or_404(note_id)
    ext = n['filename'].rsplit('.', 1)[-1].lower()
    if ext in ('pdf', 'png', 'jpg', 'jpeg'):
        return send_from_directory(app.config['UPLOAD_FOLDER'], n['filename'], as_attachment=False)
    flash('ไฟล์นี้ไม่รองรับการพรีวิวในเบราว์เซอร์ กรุณากดดาวน์โหลด', 'info')
    return redirect(url_for('note_detail', note_id=note_id))

@app.route('/download/note/<note_id>')
def download_note(note_id):
    """ดาวน์โหลดไฟล์จาก note_id"""
    n, _ = _get_note_or_404(note_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], n['filename'], as_attachment=True)

# -------- Routes --------
@app.route('/')
def home():
    # เปิดเว็บให้เข้า login เสมอ
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # GET: เคลียร์ session และแสดงหน้า login
    if request.method == 'GET':
        session.clear()
        return render_template('login.html')

    # POST: ตรวจรหัส
    sid = request.form['student_id']
    pwd = request.form['password']
    user = users.get(sid)
    if user and user['password'] == pwd:
        session['student_id'] = sid
        session['fullname'] = user['fullname']
        return redirect(url_for('dashboard'))

    flash('รหัสนักศึกษาหรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        sid = request.form['student_id']
        pwd = request.form['password']
        fullname = request.form.get('fullname', 'ผู้ใช้ใหม่')

        if sid in users:
            flash('รหัสนักศึกษานี้มีผู้ใช้งานแล้ว', 'danger')
        else:
            users[sid] = {'password': pwd, 'fullname': fullname}
            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))

# ---- Dashboard + Search/Filter ----
@app.route('/dashboard')
def dashboard():
    if not require_login(): return redirect(url_for('login'))
    q   = request.args.get('q', '').strip()
    cat = request.args.get('category', '').strip()
    me  = session['student_id']
    liked_ids = likes.get(me, set())

    def match(n):
        ok = True
        if q:
            ql = q.lower()
            ok = (ql in n['title'].lower()) or (ql in n['subject'].lower())
        if ok and cat:
            ok = (n['faculty'] == cat)
        return ok

    data = []
    for nid, n in sorted(notes.items(), key=lambda kv: kv[1]['created_at'], reverse=True):
        if match(n):
            data.append({**n, 'id': nid, 'liked': (nid in liked_ids)})

    return render_template('dashboard.html', notes=data, categories=CATEGORIES, q=q, cat=cat, library_mode=False)

# ---- Library (ของฉัน + ที่ถูกใจ) ----
@app.route('/library')
def library():
    if not require_login(): return redirect(url_for('login'))
    me = session['student_id']
    liked_ids = likes.get(me, set())

    my_notes, liked_notes = [], []

    for nid, n in notes.items():
        if n['uploader'] == me:
            my_notes.append({**n, 'id': nid, 'liked': (nid in liked_ids)})

    for nid in liked_ids:
        if nid in notes and notes[nid]['uploader'] != me:
            n = notes[nid]
            liked_notes.append({**n, 'id': nid, 'liked': True})

    my_notes.sort(key=lambda x: x['created_at'], reverse=True)
    liked_notes.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('library.html', my_notes=my_notes, liked_notes=liked_notes, categories=CATEGORIES)

# ---- Create Note ----
@app.route('/create-note', methods=['GET', 'POST'])
def create_note():
    if not require_login(): return redirect(url_for('login'))

    if request.method == 'POST':
        if 'note_file' not in request.files:
            flash('ไม่พบไฟล์', 'danger'); return redirect(request.url)
        file = request.files['note_file']
        if file.filename == '':
            flash('กรุณาเลือกไฟล์', 'danger'); return redirect(request.url)

        title   = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        faculty = request.form.get('faculty', '').strip()

        if not title or not subject or not faculty:
            flash('กรอกข้อมูลให้ครบ', 'danger'); return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            nid = str(uuid.uuid4())
            notes[nid] = {
                'title': title,
                'subject': subject,
                'faculty': faculty,
                'filename': filename,
                'uploader': session['student_id'],
                'like_count': 0,
                'report_count': 0,
                'created_at': datetime.utcnow().isoformat()
            }
            return redirect(url_for('dashboard'))

        flash('ชนิดไฟล์ไม่ได้รับอนุญาต', 'danger'); return redirect(request.url)

    return render_template('create_note.html', categories=CATEGORIES)

# ---- Note detail ----
@app.route('/note/<note_id>')
def note_detail(note_id):
    if not require_login(): return redirect(url_for('login'))
    n = notes.get(note_id)
    if not n:
        flash('ไม่พบโน้ตนี้', 'danger'); return redirect(url_for('dashboard'))
    return render_template('note_detail.html', note_id=note_id, note=n, comments=comments.get(note_id, []))

# (optional) เข้าถึงไฟล์โดยชื่อโดยตรง
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---- Actions: like / report / delete ----
@app.post('/note/<note_id>/like')
def like_note(note_id):
    if not require_login(): return redirect(url_for('login'))
    if note_id not in notes:
        return jsonify({'ok': False}), 404

    me = session['student_id']
    liked = likes.setdefault(me, set())

    if note_id in liked:
        liked.remove(note_id)
        notes[note_id]['like_count'] = max(0, notes[note_id]['like_count'] - 1)
        liked_now = False
    else:
        liked.add(note_id)
        notes[note_id]['like_count'] += 1
        liked_now = True

    return jsonify({'ok': True, 'liked': liked_now, 'count': notes[note_id]['like_count']})

@app.post('/note/<note_id>/report')
def report_note(note_id):
    if not require_login(): return redirect(url_for('login'))
    if note_id not in notes: return jsonify({'ok': False}), 404
    notes[note_id]['report_count'] += 1
    return jsonify({'ok': True})

@app.post('/delete-note/<note_id>')
def delete_note(note_id):
    if not require_login(): return redirect(url_for('login'))
    me = session['student_id']
    n = notes.get(note_id)
    if n and n['uploader'] == me:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], n['filename']))
        except OSError:
            pass
        notes.pop(note_id, None)
        for uid in list(likes.keys()):
            likes[uid].discard(note_id)
        comments.pop(note_id, None)
        flash('ลบโน้ตเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่สามารถลบโน้ตนี้ได้', 'danger')
    return redirect(url_for('dashboard'))

# ---- Comments ----
@app.post('/note/<note_id>/comment')
def add_comment(note_id):
    if not require_login(): return redirect(url_for('login'))
    if note_id not in notes:
        flash('ไม่พบน๊อต', 'danger'); return redirect(url_for('dashboard'))
    text = request.form.get('text', '').strip()
    if not text:
        flash('พิมพ์ข้อความก่อนนะ', 'danger'); return redirect(url_for('note_detail', note_id=note_id))
    c = {
        'id': str(uuid.uuid4()),
        'user': session['student_id'],
        'text': text,
        'created_at': datetime.utcnow().isoformat(),
        'report_count': 0
    }
    comments.setdefault(note_id, []).append(c)
    return redirect(url_for('note_detail', note_id=note_id))

@app.post('/comment/<note_id>/<cid>/report')
def report_comment(note_id, cid):
    if not require_login(): return redirect(url_for('login'))
    for c in comments.get(note_id, []):
        if c['id'] == cid:
            c['report_count'] += 1
            break
    return jsonify({'ok': True})

@app.post('/comment/<note_id>/<cid>/delete')
def delete_comment(note_id, cid):
    if not require_login(): return redirect(url_for('login'))
    me = session['student_id']; lst = comments.get(note_id, [])
    for i, c in enumerate(lst):
        if c['id'] == cid and c['user'] == me:
            lst.pop(i)
            return jsonify({'ok': True})
    return jsonify({'ok': False}), 403

if __name__ == '__main__':
    app.run(debug=True, port=5000)
