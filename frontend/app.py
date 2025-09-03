from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def register():
    return render_template('register.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    student_id = request.form['student_id']
    password = request.form['password']
    return f"ลงทะเบียนสำเร็จ: {name}, {student_id}"

if __name__ == '__main':
    app.run(debug=True)