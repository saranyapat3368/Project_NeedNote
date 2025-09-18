from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def register():
    return render_template('register.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    student_id = request.form['student_id']
    password = request.form['password']
    
    # (ถ้ามีการบันทึกลงฐานข้อมูล ให้ทำตรงนี้)

    # เสร็จแล้ว redirect ไปหน้า main_note
    return redirect(url_for('main_note'))

@app.route('/main_note')
def main_note():
    return render_template('main_note.html')

@app.route('/note')
def note():
    return render_template('note.html')

@app.route('/my_notes')
def my_note():
    return render_template('my_note.html')

if __name__ == '__main__':
    app.run(debug=True)
