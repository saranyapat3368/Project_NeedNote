from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # ใช้สำหรับ flash message

# mock data สำหรับโน้ตและคอมเมนต์
notes = {
    "1": {
        "title": "โน้ตเทคโนโลยีคอมพิวเตอร์",
        "subject": "คอมพิวเตอร์เบื้องต้น",
        "branch": "เทคโนโลยีคอมพิวเตอร์",
        "year": "1",
        "file_url": "/static/files/sample1.pdf",
        "comments": [
            {"id": "c1", "user": "user1", "text": "โน้ตดีมากครับ", "reports": 0}
        ],
        "reports": 0
    },
    "2": {
        "title": "โน้ตอิเล็กทรอนิกส์โทรคมนาคม",
        "subject": "โทรคมนาคมขั้นสูง",
        "branch": "อิเล็กทรอนิกส์โทรคมนาคม",
        "year": "2",
        "file_url": "/static/files/sample2.pdf",
        "comments": [],
        "reports": 0
    }
}

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # mock login
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # mock register to firebase
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    # ส่งโน้ตทั้งหมดไปแสดง
    return render_template('dashboard.html', notes=notes)

@app.route('/create-note', methods=['GET', 'POST'])
def create_note():
    if request.method == 'POST':
        # mock upload to firebase
        # ตัวอย่าง: รับข้อมูลจาก form และไฟล์
        title = request.form.get('title')
        subject = request.form.get('subject')
        branch = request.form.get('branch')
        year = request.form.get('year')
        # ไฟล์และข้อมูลอื่นๆ เก็บใน Firebase ฝั่งอื่น

        # สมมติเพิ่มโน้ตใหม่ใน mock data
        new_id = str(len(notes) + 1)
        notes[new_id] = {
            "title": title,
            "subject": subject,
            "branch": branch,
            "year": year,
            "file_url": "/static/files/sample_uploaded.pdf",  # ตัวอย่างไฟล์
            "comments": [],
            "reports": 0
        }
        flash("สร้างโน้ตสำเร็จ!")
        return redirect(url_for('dashboard'))
    return render_template('create_note.html')

@app.route('/note/<note_id>', methods=['GET', 'POST'])
def view_note(note_id):
    note = notes.get(note_id)
    if not note:
        flash("ไม่พบโน้ตนี้")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # ตรวจสอบว่าผู้ใช้กดคอมเมนต์หรือรายงาน
        action = request.form.get('action')

        if action == 'comment':
            user = request.form.get('user', 'Anonymous')
            comment_text = request.form.get('comment_text')
            if comment_text:
                comment_id = f"c{len(note['comments']) + 1}"
                note['comments'].append({"id": comment_id, "user": user, "text": comment_text, "reports": 0})
                flash("แสดงความคิดเห็นเรียบร้อย")
            else:
                flash("กรุณากรอกข้อความคอมเมนต์")
        
        elif action == 'report_note':
            note['reports'] += 1
            flash("รายงานโน้ตเรียบร้อย")
        
        elif action == 'report_comment':
            comment_id = request.form.get('comment_id')
            for c in note['comments']:
                if c['id'] == comment_id:
                    c['reports'] += 1
                    flash("รายงานคอมเมนต์เรียบร้อย")
                    break

        return redirect(url_for('view_note', note_id=note_id))

    return render_template('view_note.html', note=note, note_id=note_id)


if __name__ == '__main__':
    app.run(debug=True)
