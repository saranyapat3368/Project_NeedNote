import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from datetime import datetime, timedelta
from functools import wraps
from calendar import month_name

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-for-firebase-project'
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except FileNotFoundError:
    print("หาไฟล์ 'serviceAccountKey.json' ไม่เจอ! กรุณาตรวจสอบว่าไฟล์อยู่ในตำแหน่งที่ถูกต้อง")
    exit()

# ตรวจสอบการล็อกอิน
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # ตรวจสอบผู้ใช้
            user = auth.get_user_by_email(email)

            # ตรวจสอบรหัสผ่าน (Firebase Admin SDK ไม่มีฟังก์ชันตรวจ password โดยตรง)
            # ต้องใช้ Firebase Auth client หรือ custom token ใน frontend
            # ถ้าเป็นตัวอย่างทดสอบ ให้สมมติ password ถูกต้องสำหรับ demo
            # (สำหรับ production ต้องใช้ Firebase Auth client)

            # ตรวจสอบ Role
            claims = user.custom_claims or {}
            role = claims.get('role', 'User')

            if email == "admin@kmitl.com" and password == "123456789":
                auth.set_custom_user_claims(user.uid, {'role': 'Admin'})
                role = 'Admin'

            # เก็บ session
            session['user'] = {'email': user.email, 'uid': user.uid, 'role': role}

            # บันทึก log
            db.collection('loginHistory').add({'email': user.email, 'timestamp': datetime.utcnow()})

            # ไปหน้าตาม role
            if role == 'Admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('user_homepage'))

        except auth.UserNotFoundError:
            flash("อีเมลนี้ยังไม่ได้สมัครสมาชิก")
            return redirect(url_for('register'))
        except Exception as e:
            flash(f"เกิดข้อผิดพลาดในการล็อกอิน: {e}")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # ตรวจสอบว่ามีผู้ใช้นี้อยู่แล้ว
            try:
                user = auth.get_user_by_email(email)
                flash("อีเมลนี้มีอยู่แล้ว กรุณาเข้าสู่ระบบ")
                return redirect(url_for('login'))
            except auth.UserNotFoundError:
                # สร้างผู้ใช้ใหม่
                user = auth.create_user(email=email, password=password)
                auth.set_custom_user_claims(user.uid, {'role': 'User'})
                flash("สมัครสมาชิกสำเร็จ! โปรดเข้าสู่ระบบ")
                return redirect(url_for('login'))

        except Exception as e:
            flash(f"เกิดข้อผิดพลาด: {e}")
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/user_homepage')
@login_required
def user_homepage():
    user = session.get('user', {})
    user_email = user.get('email', 'ไม่ทราบ')
    return render_template('user_homepage.html', user_email=user_email, show_back_button=False)


# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# Main Pages
# หน้า Dashboard
@app.route('/')
@login_required
def dashboard():
    try:
        total_users = len(auth.list_users().users)
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        logins_today_query = db.collection('loginHistory').where('timestamp', '>=', today_start).stream()
        logins_today = len(list(logins_today_query))
        total_views = len(list(db.collection('pageViews').stream()))
        total_notes = len(list(db.collection('notes').stream()))
    except Exception as e:
        flash(f"ไม่สามารถโหลดข้อมูลสถิติได้: {e}")
        total_users, logins_today, total_views, total_notes = 0, 0, 0, 0

    stats = {
        'total_users': total_users, 'logins_today': logins_today,
        'total_views': total_views, 'total_notes': total_notes
    }
    return render_template('dashboard.html', stats=stats, show_back_button=False)

# Users Management
@app.route('/users')
@login_required
def users_management():
    users_list = []
    try:
        for user in auth.list_users().iterate_all():
            role = user.custom_claims.get('role', 'User') if user.custom_claims else 'User'
            users_list.append({
                'uid': user.uid, 'email': user.email,
                'name': user.email.split('@')[0], 'role': role
            })
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการดึงข้อมูลผู้ใช้: {e}")
    return render_template('users.html', users=users_list, show_back_button=False)

# Settings
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', show_back_button=False)

# Manage Notes
@app.route('/manage-notes')
@login_required
def manage_notes():
    search_query = request.args.get('search_query', '')
    
    try:
        year = int(request.args.get('year', datetime.utcnow().year))
        month = int(request.args.get('month', datetime.utcnow().month))
    except ValueError:
        year = datetime.utcnow().year
        month = datetime.utcnow().month
    
    selected_date = datetime(year, month, 1)
    prev_month_date = selected_date - timedelta(days=1)
    prev_month = {'year': prev_month_date.year, 'month': prev_month_date.month}
    try: next_month_date = selected_date.replace(day=28) + timedelta(days=4)
    except ValueError: next_month_date = selected_date.replace(day=1, month=selected_date.month+1)
    next_month = {'year': next_month_date.year, 'month': next_month_date.month}
    month_header = f"Popular Notes for {month_name[month]} {year}"

    notes_list = []

    if search_query:
        month_header = f"ผลการค้นหาสำหรับ '{search_query}'"
        search_query_lower = search_query.lower()
        all_notes = db.collection('notes').stream()
        for note in all_notes:
            note_data = note.to_dict()
            subject_lower = note_data.get('subject_lowercase', '')
            if search_query_lower in subject_lower:
                notes_list.append({
                    'rank': '-', 'owner': note_data.get('ownerEmail', 'N/A'),
                    'subject': note_data.get('subject', 'N/A'),
                    'saves': note_data.get('viewCount', 0), 'views': '-'
                })
    else:
        start_of_month = datetime(year, month, 1)
        try: end_of_month = start_of_month.replace(month=start_of_month.month + 1)
        except ValueError: end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1)
        
        views_query = db.collection('pageViews').where('timestamp', '>=', start_of_month).where('timestamp', '<', end_of_month).stream()
        monthly_views = {}
        for view in views_query:
            note_id = str(view.to_dict().get('note_id'))
            if note_id: monthly_views[note_id] = monthly_views.get(note_id, 0) + 1
        
        notes_ref = db.collection('notes').stream()
        temp_notes = []
        for note in notes_ref:
            note_data = note.to_dict()
            note_id_num = note_data.get('note_id')
            if note_id_num:
                temp_notes.append({
                    'owner': note_data.get('ownerEmail', 'N/A'), 'subject': note_data.get('subject', 'N/A'),
                    'saves': note_data.get('viewCount', 0), 'monthly_views': monthly_views.get(str(note_id_num), 0)
                })
        
        sorted_notes = sorted(temp_notes, key=lambda x: x['monthly_views'], reverse=True)
        
        for i, note in enumerate(sorted_notes):
            notes_list.append({
                'rank': i + 1, 'owner': note['owner'], 'subject': note['subject'],
                'saves': note['saves'], 'views': note['monthly_views']
            })

    return render_template('manage_notes.html', notes=notes_list, search_query=search_query,
                           month_header=month_header, prev_month=prev_month,
                           next_month=next_month, show_back_button=True)


# หน้ารายงาน
# Dashboard แสดงกราฟ
@app.route('/dashboard/details/<metric>')
@login_required
def dashboard_details(metric):
    return render_template('dashboard_details.html', metric_name=metric.replace('_', ' ').title(), show_back_button=True)

# หน้ารายงานโน้ตไม่เหมาะสม
@app.route('/reports/inappropriate-notes')
@login_required
def report_inappropriate_notes():
    reports_list = []
    try:
        reports_query = db.collection('reportedNotes').where('status', '==', 'pending').stream()
        for i, report in enumerate(reports_query):
            report_data = report.to_dict()
            note_doc_id = report_data.get('noteDocId')
            note_doc = db.collection('notes').document(note_doc_id).get()
            if note_doc.exists:
                note_data = note_doc.to_dict()
                reports_list.append({
                    'rank': i + 1, 'reportId': report.id, 'noteDocId': note_doc_id,
                    'owner': note_data.get('ownerEmail', 'N/A'), 'subject': note_data.get('subject', 'N/A'),
                    'reason': report_data.get('reason', 'No reason provided.')
                })
    except Exception as e:
        flash(f"Error fetching reports: {e}")
    return render_template('reporte_notes.html', reports=reports_list, show_back_button=True)

# หน้ารายงานลิขสิทธิ์
@app.route('/reports/copyright')
@login_required
def report_copyright():
    reports_list = []
    try:
        reports_query = db.collection('copyrightReports').where('status', '==', 'pending').stream()
        for i, report in enumerate(reports_query):
            report_data = report.to_dict()
            note_doc_id = report_data.get('noteDocId')
            note_doc = db.collection('notes').document(note_doc_id).get()
            if note_doc.exists:
                note_data = note_doc.to_dict()
                reports_list.append({
                    'rank': i + 1, 'reportId': report.id, 'noteDocId': note_doc_id,
                    'owner': note_data.get('ownerEmail', 'N/A'), 'subject': note_data.get('subject', 'N/A'),
                    'reason': report_data.get('reason', 'N/A'), 'evidence': report_data.get('evidence', 'No evidence provided.')
                })
    except Exception as e:
        flash(f"Error fetching copyright reports: {e}")
    return render_template('report_copyright.html', reports=reports_list, show_back_button=True)

# หน้ารายงานคอมเมนต์
@app.route('/reports/inappropriate-comments')
@login_required
def report_inappropriate_comments():
    reports_list = []
    try:
        reports_query = db.collection('reportedComments').where('status', '==', 'pending').stream()
        for i, report in enumerate(reports_query):
            report_data = report.to_dict()
            reports_list.append({
                'rank': i + 1, 'reportId': report.id, 'commentDocId': report_data.get('commentDocId'),
                'commentText': report_data.get('commentText', 'N/A'), 'reason': report_data.get('reason', 'No reason provided.')
            })
    except Exception as e:
        flash(f"Error fetching comment reports: {e}")
    return render_template('report_comments.html', reports=reports_list, show_back_button=True)


# Actions
@app.route('/delete_user/<uid>')
@login_required
def delete_user(uid):
    try:
        auth.delete_user(uid)
        flash(f"ผู้ใช้ {uid} ถูกลบแล้ว")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบผู้ใช้: {e}")
    return redirect(url_for('users_management'))

@app.route('/toggle_admin/<uid>')
@login_required
def toggle_admin(uid):
    try:
        user = auth.get_user(uid)
        current_role = user.custom_claims.get('role') if user.custom_claims else None
        if current_role == 'Admin':
            auth.set_custom_user_claims(uid, None)
            flash(f"{user.email} ไม่ได้เป็น Admin อีกต่อไป")
        else:
            auth.set_custom_user_claims(uid, {'role': 'Admin'})
            flash(f"{user.email} ได้รับสิทธิ์เป็น Admin แล้ว")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการอัปเดต Role: {e}")
    return redirect(url_for('users_management'))

@app.route('/resolve_report_delete_note/<report_id>/<note_doc_id>')
@login_required
def resolve_report_delete_note(report_id, note_doc_id):
    try:
        db.collection('notes').document(note_doc_id).delete()
        db.collection('reportedNotes').document(report_id).update({'status': 'resolved'})
        flash(f"โน้ต ({note_doc_id}) ถูกลบและรายงานถูกจัดการแล้ว")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาด: {e}")
    return redirect(url_for('report_inappropriate_notes'))

@app.route('/resolve_copyright_report/<report_id>/<note_doc_id>')
@login_required
def resolve_copyright_report(report_id, note_doc_id):
    try:
        db.collection('notes').document(note_doc_id).delete()
        db.collection('copyrightReports').document(report_id).update({'status': 'resolved'})
        flash(f"โน้ต ({note_doc_id}) ถูกลบและรายงานถูกจัดการแล้ว")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาด: {e}")
    return redirect(url_for('report_copyright'))

@app.route('/resolve_comment_report/<report_id>/<comment_doc_id>')
@login_required
def resolve_comment_report(report_id, comment_doc_id):
    try:
        print(f"จำลองการลบคอมเมนต์ ID: {comment_doc_id}")
        db.collection('reportedComments').document(report_id).update({'status': 'resolved'})
        flash(f"คอมเมนต์ ({comment_doc_id}) ถูกลบและรายงานถูกจัดการแล้ว")
    except Exception as e:
        flash(f"เกิดข้อผิดพลาด: {e}")
    return redirect(url_for('report_inappropriate_comments'))

# API กราฟ
@app.route('/api/logins-chart-data')
@login_required
def logins_chart_data():
    labels, data = [], []
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

@app.route('/api/views-chart-data')
@login_required
def views_chart_data():
    labels, data = [], []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        labels.append(day.strftime("%d/%m"))
        query = db.collection('pageViews').where('timestamp', '>=', day_start).where('timestamp', '<=', day_end).stream()
        count = len(list(query))
        data.append(count)
    return jsonify({'labels': labels, 'data': data})

@app.route('/api/notes-chart-data')
@login_required
def notes_chart_data():
    labels, data = [], []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        labels.append(day.strftime("%d/%m"))
        query = db.collection('notes').where('createdAt', '>=', day_start).where('createdAt', '<=', day_end).stream()
        count = len(list(query))
        data.append(count)
    return jsonify({'labels': labels, 'data': data})

@app.route('/api/users-chart-data')
@login_required
def users_chart_data():
    labels, data = [], []
    today = datetime.utcnow().date()
    seven_days_keys = [(today - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    daily_counts = {day_key: 0 for day_key in seven_days_keys}
    try:
        for user in auth.list_users().iterate_all():
            creation_date = datetime.utcfromtimestamp(user.user_metadata.creation_timestamp / 1000).strftime("%d/%m")
            if creation_date in daily_counts:
                daily_counts[creation_date] += 1
    except Exception as e:
        print(f"Could not fetch user data for chart: {e}")
    labels = list(daily_counts.keys())
    data = list(daily_counts.values())
    return jsonify({'labels': labels, 'data': data})


# ทดสอบฟีเจอร์ต่างๆ
@app.route('/view_note/<int:note_id>')
def view_note(note_id):
    db.collection('pageViews').add({'note_id': note_id, 'timestamp': datetime.utcnow()})
    try:
        notes_with_id_field = list(db.collection('notes').where('note_id', '==', note_id).limit(1).stream())
        if notes_with_id_field:
            note_ref = notes_with_id_field[0].reference
            note_ref.update({'viewCount': firestore.Increment(1)})
    except: pass
    return f"คุณกำลังดูโน้ต ID ที่ {note_id}! (บันทึกการดูแล้ว)"

# ลองทำแอดมิน
@app.route('/make-me-admin')
def make_me_admin():
    try:
        email_to_make_admin = "admin@kmitl.com" 
        user = auth.get_user_by_email(email_to_make_admin)
        auth.set_custom_user_claims(user.uid, {'role': 'Admin'})
        return f"สำเร็จ: {email_to_make_admin} ได้รับสิทธิ์เป็น Admin แล้ว!"
    except Exception as e:
        return f"เกิดข้อผิดพลาด: {e}"

# สร้างโน้ตตัวอย่าง
@app.route('/create_sample_notes')
def create_sample_notes():
    notes_data = [
        {'ownerEmail': 'user1@example.com', 'subject': 'Calculus I', 'subject_lowercase': 'calculus i', 'viewCount': 0, 'note_id': 1, 'createdAt': datetime.utcnow() - timedelta(days=2)},
        {'ownerEmail': 'user2@example.com', 'subject': 'Intro to Python', 'subject_lowercase': 'intro to python', 'viewCount': 0, 'note_id': 2, 'createdAt': datetime.utcnow() - timedelta(days=1)},
        {'ownerEmail': 'user1@example.com', 'subject': 'Physics for Engineers', 'subject_lowercase': 'physics for engineers', 'viewCount': 0, 'note_id': 3, 'createdAt': datetime.utcnow()},
        {'ownerEmail': 'user3@example.com', 'subject': 'Organic Chemistry', 'subject_lowercase': 'organic chemistry', 'viewCount': 0, 'note_id': 4, 'createdAt': datetime.utcnow()}
    ]
    for note in notes_data:
        db.collection('notes').add(note)
    return "สร้างโน้ตตัวอย่างที่มี subject_lowercase สำเร็จ!"

# สร้างรายงานโน้ต
@app.route('/create_sample_reports')
def create_sample_reports():
    notes_ref = db.collection('notes').limit(2).stream()
    note_ids_to_report = [note.id for note in notes_ref]
    if len(note_ids_to_report) < 2: return "Please create sample notes first"
    reports_data = [
        {'noteDocId': note_ids_to_report[0], 'reason': 'เนื้อหาไม่เหมาะสม', 'reporterId': 'user_A', 'status': 'pending', 'reportedAt': datetime.utcnow()},
        {'noteDocId': note_ids_to_report[1], 'reason': 'คัดลอกเนื้อหา', 'reporterId': 'user_B', 'status': 'pending', 'reportedAt': datetime.utcnow()}
    ]
    for report in reports_data: db.collection('reportedNotes').add(report)
    return "สร้างรายงาน (โน้ตไม่เหมาะสม) ตัวอย่างสำเร็จ!"

# สร้างรายงานลิขสิทธิ์
@app.route('/create_sample_copyright_reports')
def create_sample_copyright_reports():
    notes_ref = db.collection('notes').limit(2).stream()
    note_ids_to_report = [note.id for note in notes_ref]
    if not note_ids_to_report: return "Please create sample notes first"
    reports_data = [
        {'noteDocId': note_ids_to_report[0], 'reason': 'คัดลอกเว็บ A', 'evidence': 'https://example.com/A', 'reporterId': 'user_C', 'status': 'pending', 'reportedAt': datetime.utcnow()},
        {'noteDocId': note_ids_to_report[1], 'reason': 'ใช้รูปภาพมีลิขสิทธิ์', 'evidence': 'https://example.com/image', 'reporterId': 'user_D', 'status': 'pending', 'reportedAt': datetime.utcnow()}
    ]
    for report in reports_data: db.collection('copyrightReports').add(report)
    return "สร้างรายงาน (ลิขสิทธิ์) ตัวอย่างสำเร็จ!"

# สร้างรายงานคอมเมน
@app.route('/create_sample_comment_reports')
def create_sample_comment_reports():
    reports_data = [
        {'commentDocId': 'comment_xyz123', 'commentText': 'เขียนมั่วมาก', 'reason': 'คำหยาบ', 'reporterId': 'user_X', 'status': 'pending', 'reportedAt': datetime.utcnow()},
        {'commentDocId': 'comment_abc789', 'commentText': 'ไปลอกมา', 'reason': 'สแปม', 'reporterId': 'user_Y', 'status': 'pending', 'reportedAt': datetime.utcnow()}
    ]
    for report in reports_data: db.collection('reportedComments').add(report)
    return "สร้างรายงาน (คอมเมนต์) ตัวอย่างสำเร็จ!"

if __name__ == '__main__':
    app.run(debug=True, port=5001)