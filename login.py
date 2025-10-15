# app.py

import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, redirect, url_for, request, flash, session
from datetime import datetime
from functools import wraps

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-for-firebase-project'

# --- Firebase Initialization ---
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase connected successfully.")
except FileNotFoundError:
    print("FATAL ERROR: 'serviceAccountKey.json' not found. Please ensure the file is in the root directory.")
    exit()

# --- Middleware ---
def login_required(f):
    """Decorator to ensure user is logged in before accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('กรุณาเข้าสู่ระบบก่อน')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the login process."""
    if 'user' in session:
        return redirect(url_for('dashboard')) # ถ้าล็อกอินอยู่แล้ว ให้ไป dashboard เลย

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # This is a placeholder for actual authentication.
        # In a real app, you would verify the password with Firebase Auth.
        if email == "admin@kmitl.com" and password == "password123":
            try:
                user = auth.get_user_by_email(email)
                session['user'] = {'email': user.email, 'uid': user.uid}
                # Log login history
                db.collection('loginHistory').add({
                    'email': user.email,
                    'timestamp': datetime.utcnow()
                })
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Authentication error: {e}")
                return redirect(url_for('login'))
        else:
            flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง!')
            return redirect(url_for('login'))
    
    return render_template('login.html', show_back_button=False)

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """A protected dashboard page."""
    # This is a placeholder for your main admin page after login.
    return f"<h1>Welcome to Dashboard, {session['user']['email']}!</h1> <a href='/logout'>Logout</a>"

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles the user registration process."""
    if request.method == 'POST':
        # รับข้อมูลจากฟอร์มที่แก้ไขแล้ว
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not all([full_name, email, password]):
            flash('กรุณากรอกข้อมูลให้ครบทุกช่อง')
            return redirect(url_for('register'))

        try:
            # 1. สร้างผู้ใช้ใน Firebase Authentication พร้อมกับ display_name
            new_user = auth.create_user(
                email=email,
                password=password,
                display_name=full_name
            )

            # 2. บันทึก full_name ลงใน Firestore
            user_data = {
                'full_name': full_name,
                'email': email
            }
            db.collection('users').document(new_user.uid).set(user_data)
            
            flash('ลงทะเบียนสำเร็จแล้ว! กรุณาเข้าสู่ระบบด้วยบัญชีใหม่ของคุณ')
            return redirect(url_for('login'))

        except auth.EmailAlreadyExistsError:
            flash('อีเมลนี้มีผู้ใช้งานในระบบแล้ว')
            return redirect(url_for('register'))
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}')
            return redirect(url_for('register'))
            
    # ถ้าเป็น GET request ให้แสดงหน้าฟอร์มลงทะเบียน
    return render_template('register.html', show_back_button=True)


# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)