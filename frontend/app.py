import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# จำลองฐานข้อมูลโน้ตง่าย ๆ เป็น dict
# key = username, value = list ของ dict โน้ต {title, filename}
user_notes = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # ตัวอย่างตรวจสอบง่าย ๆ
        if username == 'user' and password == 'pass':
            session['username'] = username
            if username not in user_notes:
                user_notes[username] = []
            return redirect(url_for('mainnote'))
        else:
            flash("Login failed. Try again.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/mainnote')
def mainnote():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('note.html', username=session['username'])

@app.route('/mynote')
def mynote():
    if 'username' not in session:
        return redirect(url_for('login'))
    notes = user_notes.get(session['username'], [])
    return render_template('my_note.html', notes=notes)

@app.route('/create_note', methods=['GET', 'POST'])
def create_note():
    if 'username' not in session:
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

            # บันทึกโน้ตของ user
            user_notes[session['username']].append({'title': title, 'filename': filename})
            flash("Note created successfully!")
            return redirect(url_for('mynote'))
        else:
            flash("Invalid file or no file uploaded")
    
    return render_template('create_note.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        student_id = request.form['student_id']
        password = request.form['password']

        # ตรวจสอบว่าชื่อผู้ใช้ซ้ำหรือไม่
        if username in user_notes:
            flash("Username already exists, please try another.")
            return redirect(url_for('register'))

        # สร้าง user ใหม่ใน dict (จำลองฐานข้อมูล)
        user_notes[username] = []

        flash("Register successful! Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)
