import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import uuid

# --- 1. การตั้งค่าพื้นฐาน ---
UPLOAD_FOLDER = 'static/uploads' # โฟลเดอร์สำหรับเก็บไฟล์
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'} # นามสกุลไฟล์ที่อนุญาต

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'a-super-secret-key-for-sessions' # Key ลับสำหรับระบบ Session

# สร้างโฟลเดอร์ uploads ถ้ายังไม่มี
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 2. "ฐานข้อมูล" จำลอง (ใช้ Dictionary เก็บข้อมูลชั่วคราว) ---
# ในโปรเจกต์จริง ส่วนนี้จะถูกแทนที่ด้วยฐานข้อมูลจริงๆ เช่น SQLite, PostgreSQL
users = {}  # รูปแบบ: {'student_id': {'password': '...', 'fullname': '...'}}
notes = {}  # รูปแบบ: {'note_id': { 'subject': ..., 'filename': ... }}


# --- 3. ฟังก์ชันช่วยเหลือ ---
def allowed_file(filename):
    """ตรวจสอบว่านามสกุลไฟล์ได้รับอนุญาตหรือไม่"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 4. ส่วนของหน้าเว็บ (Routes) ---

@app.route('/')
def home():
    """หน้าแรก: ถ้าล็อกอินแล้วไป dashboard, ถ้ายังให้ไปหน้า login"""
    if 'student_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = request.form['password']
        
        user = users.get(student_id)
        if user and user['password'] == password:
            session['student_id'] = student_id
            session['fullname'] = user['fullname']
            flash('เข้าสู่ระบบสำเร็จ!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('รหัสนักศึกษาหรือรหัสผ่านไม่ถูกต้อง', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ฟังก์ชันสำหรับหน้าลงทะเบียน"""
    if request.method == 'POST':
        # รับข้อมูลจากฟอร์ม
        student_id = request.form['student_id']
        password = request.form['password']
        fullname = request.form.get('fullname', 'ผู้ใช้ใหม่')
        
        # ตรวจสอบว่ามีรหัสนักศึกษานี้ในระบบหรือยัง
        if student_id in users:
            flash('รหัสนักศึกษานี้มีผู้ใช้งานแล้ว', 'danger')
        else:
            # เพิ่มผู้ใช้ใหม่เข้าระบบ
            users[student_id] = {'password': password, 'fullname': fullname}
            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))
            
    # ถ้าเป็น method GET (เปิดหน้าเว็บครั้งแรก) ให้แสดงฟอร์ม
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear() # ลบข้อมูลทั้งหมดออกจาก session
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """หน้าแสดงโน้ตทั้งหมด"""
    if 'student_id' not in session:
        flash('กรุณาเข้าสู่ระบบก่อน', 'danger')
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', notes=notes)

@app.route('/create-note', methods=['GET', 'POST'])
def create_note():
    """หน้าอัปโหลดโน้ต"""
    if 'student_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'note_file' not in request.files:
            flash('ไม่พบไฟล์ในฟอร์ม', 'danger')
            return redirect(request.url)
        
        file = request.files['note_file']

        if file.filename == '':
            flash('กรุณาเลือกไฟล์ที่จะอัปโหลด', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            note_id = str(uuid.uuid4())
            notes[note_id] = {
                'subject': request.form['subject'],
                'faculty': request.form.get('faculty', ''),  # ถ้าไม่มีให้ใช้ค่าว่าง
                'filename': filename,
                'uploader': session['student_id']
            }
            
            flash('อัปโหลดโน้ตสำเร็จ!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('ชนิดไฟล์ไม่ได้รับอนุญาต (ต้องเป็น PDF, DOC, JPG, PNG เท่านั้น)', 'danger')
            return redirect(request.url)
            
    return render_template('create_note.html')

@app.route('/delete-note/<note_id>', methods=['POST'])
def delete_note(note_id):
    """ฟังก์ชันสำหรับลบโน้ต"""
    if 'student_id' not in session:
        return redirect(url_for('login'))

    note = notes.get(note_id)
    if note and note['uploader'] == session['student_id']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], note['filename']))
        except OSError as e:
            print(f"Error deleting file: {e.strerror}")

        del notes[note_id]
        flash('ลบโน้ตเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่สามารถลบโน้ตนี้ได้', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """ทำให้สามารถเข้าถึงไฟล์ที่อัปโหลดได้โดยตรงผ่าน URL"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- 5. สั่งให้โปรแกรมทำงาน ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)

