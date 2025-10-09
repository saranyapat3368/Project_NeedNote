import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-for-firebase-project'

try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except FileNotFoundError:
    print("Error: 'serviceAccountKey.json' not found. Please check the file path.")
    exit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def dashboard():
    try:
        total_users = len(auth.list_users().users)
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        logins_today_query = db.collection('loginHistory').where('timestamp', '>=', today_start).stream()
        logins_today = len(list(logins_today_query))
        total_views = len(list(db.collection('pageViews').stream()))
    except Exception as e:
        flash(f"Could not load dashboard stats: {e}")
        total_users, logins_today, total_views = 0, 0, 0

    stats = {
        'total_users': total_users,
        'logins_today': logins_today,
        'total_views': total_views
    }
    return render_template('dashboard.html', stats=stats)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == "admin@kmitl.com" and password == "password123":
            try:
                user = auth.get_user_by_email(email)
                session['user'] = {'email': user.email, 'uid': user.uid}

                log_data = {'email': user.email, 'timestamp': datetime.utcnow()}
                db.collection('loginHistory').add(log_data)
                
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Authentication error: {e}")
                return redirect(url_for('login'))
        else:
            flash('Email or Password incorrect!')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/users')
@login_required
def users_management():
    users_list = []
    try:
        for user in auth.list_users().iterate_all():
            role = user.custom_claims.get('role', 'User') if user.custom_claims else 'User'
            users_list.append({
                'uid': user.uid,
                'email': user.email,
                'name': user.email.split('@')[0],
                'role': role
            })
    except Exception as e:
        flash(f"Error fetching users: {e}")

    return render_template('users.html', users=users_list)


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@app.route('/delete_user/<uid>')
@login_required
def delete_user(uid):
    try:
        auth.delete_user(uid)
        flash(f"User {uid} has been deleted.")
    except Exception as e:
        flash(f"Error deleting user: {e}")
    return redirect(url_for('users_management'))


@app.route('/toggle_admin/<uid>')
@login_required
def toggle_admin(uid):
    try:
        user = auth.get_user(uid)
        current_role = user.custom_claims.get('role') if user.custom_claims else None

        if current_role == 'Admin':
            auth.set_custom_user_claims(uid, None)
            flash(f"{user.email} is no longer an Admin.")
        else:
            auth.set_custom_user_claims(uid, {'role': 'Admin'})
            flash(f"{user.email} is now an Admin.")
    except Exception as e:
        flash(f"Error updating role: {e}")
    return redirect(url_for('users_management'))



@app.route('/api/chart-data')
@login_required
def chart_data():
    labels = []
    data = []
    today = datetime.utcnow().date()
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        labels.append(day.strftime("%d/%m"))
        query = db.collection('loginHistory').where('timestamp', '>=', day_start).where('timestamp', '<=', day_end).stream()
        count = len(list(query))
        data.append(count)
        
    return jsonify({'labels': labels, 'data': data})


@app.route('/view_note/<int:note_id>')
def view_note(note_id):
    view_data = {'note_id': note_id, 'timestamp': datetime.utcnow()}
    db.collection('pageViews').add(view_data)
    return f"You are viewing Note ID {note_id}! (View has been logged to Firestore)"

@app.route('/make-me-admin')
def make_me_admin():
    try:
        email_to_make_admin = "admin@kmitl.com" 
        user = auth.get_user_by_email(email_to_make_admin)
        auth.set_custom_user_claims(user.uid, {'role': 'Admin'})
        return f"SUCCESS: {email_to_make_admin} is now an Admin!"
    except Exception as e:
        return f"An error occurred: {e}"

@app.route('/manage-notes')
@login_required
def manage_notes():
    return render_template('manage_notes.html')

@app.route('/reports/inappropriate-notes')
@login_required
def report_inappropriate_notes():
    return render_template('report_notes.html')

@app.route('/reports/copyright')
@login_required
def report_copyright():
    return render_template('report_copyright.html')

@app.route('/reports/inappropriate-comments')
@login_required
def report_inappropriate_comments():
    return render_template('report_comments.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)