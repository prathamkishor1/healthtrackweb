from flask import Flask, render_template, request, redirect, session, send_file, flash, Response
import mysql.connector
from config import DB_CONFIG
from datetime import datetime
from weasyprint import HTML
from io import StringIO
import csv

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Connect to MySQL
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# -------------------- USER ROUTES --------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
    user = cursor.fetchone()
    if user:
        session['user_id'] = user[0]
        return redirect('/dashboard')
    else:
        return "Invalid credentials!"

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']

    cursor.execute("SELECT * FROM health_logs WHERE user_id=%s ORDER BY date DESC", (user_id,))
    logs = cursor.fetchall()

    cursor.execute("SELECT name FROM users WHERE id=%s", (user_id,))
    user_name = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(temperature), AVG(spo2), AVG(sugar_level) FROM health_logs WHERE user_id=%s", (user_id,))
    averages = cursor.fetchone()

    # Fetch messages for the logged-in patient
    cursor.execute("""
        SELECT m.message, m.sent_at, d.name
        FROM messages m
        JOIN doctors d ON m.sender_doctor_id = d.id
        WHERE m.receiver_patient_id = %s
        ORDER BY m.sent_at DESC
    """, (user_id,))
    messages = cursor.fetchall()

    suggestions = []
    if logs:
        latest_log = logs[0]
        temperature, spo2, sugar = float(latest_log[3]), int(latest_log[5]), int(latest_log[6])

        if temperature >= 101:
            suggestions.append("🌡️ You have a fever. Drink fluids and consider paracetamol.")
        elif temperature <= 95:
            suggestions.append("❄️ Low body temperature. Stay warm and hydrated.")

        if spo2 < 92:
            suggestions.append("🫁 Low SpO2 detected. Practice deep breathing and consult a doctor.")

        if sugar > 200:
            suggestions.append("🍭 High blood sugar. Reduce sugar intake and monitor closely.")

        if sugar < 70:
            suggestions.append("🍬 Low blood sugar. Have a quick snack or fruit juice.")

    return render_template('dashboard.html', logs=logs, data=logs, user_name=user_name, averages=averages, suggestions=suggestions, messages=messages)


@app.route('/add_log', methods=['POST'])
def add_log():
    user_id = session['user_id']
    temperature = request.form['temperature']
    bp = request.form['blood_pressure']
    spo2 = request.form['spo2']
    sugar = request.form['sugar']
    note = request.form.get('note', '')
    log_date = datetime.now()

    cursor.execute("""
        INSERT INTO health_logs (user_id, date, temperature, blood_pressure, spo2, sugar_level, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, log_date, temperature, bp, spo2, sugar, note))
    db.commit()

    alerts = []
    if float(temperature) > 101:
        alerts.append("⚠️ High temperature detected! Possible fever.")
    if int(spo2) < 92:
        alerts.append("⚠️ Low SpO2 detected! Risk of low oxygen saturation.")
    if int(sugar) > 200:
        alerts.append("⚠️ High blood sugar detected! Possible hyperglycemia.")

    for alert in alerts:
        flash(alert)

    return redirect('/dashboard')

@app.route('/send_patient_message/<int:doctor_id>', methods=['POST'])
def send_patient_message(doctor_id):
    if 'user_id' not in session:
        return redirect('/login')

    message_text = request.form['message']
    patient_id = session['user_id']

    cursor.execute("""
        INSERT INTO messages (sender_doctor_id, receiver_patient_id, message, sender_type)
        VALUES (%s, %s, %s, %s)
    """, (doctor_id, patient_id, message_text, 'patient'))
    db.commit()

    flash("✅ Message sent to your doctor.")
    return redirect('/dashboard')

@app.route('/delete_message/<int:message_id>')
def delete_message(message_id):
    if 'user_id' not in session:
        return redirect('/login')

    cursor.execute("DELETE FROM messages WHERE id=%s AND receiver_patient_id=%s", (message_id, session['user_id']))
    db.commit()
    flash("✅ Message deleted.")
    return redirect('/dashboard')


@app.route('/assign_doctor', methods=['GET', 'POST'])
def assign_doctor():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        patient_id = session['user_id']

        # Check if already assigned
        cursor.execute("SELECT * FROM patient_doctor WHERE patient_id=%s", (patient_id,))
        if cursor.fetchone():
            flash("❌ You’ve already assigned a doctor.")
            return redirect('/dashboard')

        # Assign doctor
        cursor.execute("INSERT INTO patient_doctor (doctor_id, patient_id) VALUES (%s, %s)", (doctor_id, patient_id))
        db.commit()
        flash("✅ Doctor assigned successfully.")
        return redirect('/dashboard')

    # Fetch doctors
    cursor.execute("SELECT id, name FROM doctors")
    doctors = cursor.fetchall()
    return render_template('assign_doctor.html', doctors=doctors)

@app.route('/messages')
def view_messages():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute("""
        SELECT m.message, m.sent_at, d.name
        FROM messages m
        JOIN doctors d ON m.sender_doctor_id = d.id
        WHERE m.receiver_patient_id = %s
        ORDER BY m.sent_at DESC
    """, (user_id,))
    messages = cursor.fetchall()

    return render_template('messages.html', messages=messages)



@app.route('/delete_log/<int:log_id>')
def delete_log(log_id):
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("DELETE FROM health_logs WHERE id=%s", (log_id,))
    db.commit()
    flash("✅ Health log deleted successfully.")
    return redirect('/dashboard')

@app.route('/clear_logs')
def clear_logs():
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("DELETE FROM health_logs WHERE user_id=%s", (session['user_id'],))
    db.commit()
    flash("✅ All logs cleared successfully.")
    return redirect('/dashboard')

@app.route('/generate_pdf')
def generate_pdf():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']

    cursor.execute("SELECT name FROM users WHERE id=%s", (user_id,))
    user_name = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM health_logs WHERE user_id=%s ORDER BY date DESC", (user_id,))
    logs = cursor.fetchall()

    rendered_html = render_template('report.html', user_name=user_name, logs=logs)
    pdf = HTML(string=rendered_html).write_pdf()

    pdf_path = f"health_report_{user_id}.pdf"
    with open(pdf_path, 'wb') as f:
        f.write(pdf)

    return send_file(pdf_path, as_attachment=True)

@app.route('/download_csv')
def download_csv():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']

    cursor.execute("""
        SELECT date, temperature, blood_pressure, spo2, sugar_level, note
        FROM health_logs
        WHERE user_id=%s
        ORDER BY date DESC
    """, (user_id,))
    logs = cursor.fetchall()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Temperature (°C)', 'BP', 'SpO2 (%)', 'Sugar (mg/dL)', 'Note'])
    cw.writerows(logs)

    output = si.getvalue()
    response = Response(output, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=health_logs.csv'
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# -------------------- DOCTOR PORTAL ROUTES --------------------

@app.route('/message_center/<int:patient_id>')
def message_center(patient_id):
    if 'doctor_id' not in session and 'user_id' != patient_id:
        return redirect('/')

    # Fetch messages between this patient and assigned doctor
    cursor.execute("""
        SELECT id, sender_type, message, sent_at FROM messages
        WHERE receiver_patient_id = %s
        ORDER BY sent_at ASC
    """, (patient_id,))
    messages = cursor.fetchall()

    # Fetch patient name
    cursor.execute("SELECT name FROM users WHERE id=%s", (patient_id,))
    patient_name = cursor.fetchone()[0]

    return render_template('message_center.html', messages=messages, patient_id=patient_id, patient_name=patient_name)


# Doctor Registration
@app.route('/doctor_register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        cursor.execute("INSERT INTO doctors (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        db.commit()
        return redirect('/doctor_login')
    return render_template('doctor_register.html')

# Doctor Login
@app.route('/doctor_login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM doctors WHERE email=%s AND password=%s", (email, password))
        doctor = cursor.fetchone()
        if doctor:
            session['doctor_id'] = doctor[0]
            return redirect('/doctor_dashboard')
        else:
            return "Invalid credentials!"
    return render_template('doctor_login.html')

# Doctor Dashboard
@app.route('/doctor_dashboard')
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect('/doctor_login')

    doctor_id = session['doctor_id']

    cursor.execute("SELECT name FROM doctors WHERE id=%s", (doctor_id,))
    doctor_name = cursor.fetchone()[0]

    # Fetch patients assigned to this doctor
    cursor.execute("""
        SELECT users.id, users.name, users.email
        FROM users
        JOIN patient_doctor ON users.id = patient_doctor.patient_id
        WHERE patient_doctor.doctor_id = %s
    """, (doctor_id,))
    patients = cursor.fetchall()

    return render_template('doctor_dashboard.html', doctor_name=doctor_name, patients=patients)


# View individual patient logs
@app.route('/view_patient/<int:patient_id>')
def view_patient(patient_id):
    if 'doctor_id' not in session:
        return redirect('/doctor_login')

    cursor.execute("SELECT * FROM health_logs WHERE user_id=%s ORDER BY date DESC", (patient_id,))
    logs = cursor.fetchall()

    cursor.execute("SELECT name FROM users WHERE id=%s", (patient_id,))
    patient_name = cursor.fetchone()[0]

    return render_template('view_patient.html', logs=logs, patient_name=patient_name)

@app.route('/send_message/<int:patient_id>', methods=['POST'])
def send_message(patient_id):
    if 'doctor_id' not in session:
        return redirect('/doctor_login')

    message_text = request.form.get('message_content')
    if not message_text:
        flash("⚠️ Message cannot be empty.")
        return redirect('/doctor_dashboard')

    doctor_id = session['doctor_id']

    cursor.execute("""
        INSERT INTO messages (sender_doctor_id, receiver_patient_id, message)
        VALUES (%s, %s, %s)
    """, (doctor_id, patient_id, message_text))
    db.commit()

    flash("✅ Message sent to patient.")
    return redirect('/doctor_dashboard')


@app.route('/message/<int:patient_id>')
def message_form(patient_id):
    if 'doctor_id' not in session:
        return redirect('/doctor_login')

    cursor.execute("SELECT name FROM users WHERE id=%s", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        return "Patient not found."

    return render_template('messages.html', patient_id=patient_id, patient_name=patient[0])

@app.route('/delete_message_center/<int:message_id>/<int:patient_id>')
def delete_message_center(message_id, patient_id):
    if 'doctor_id' not in session and 'user_id' not in session:
        return redirect('/')

    sender_type = 'doctor' if 'doctor_id' in session else 'patient'
    sender_id_field = 'sender_doctor_id' if sender_type == 'doctor' else 'receiver_patient_id'
    sender_id_value = session.get('doctor_id') if 'doctor_id' in session else session.get('user_id')

    cursor.execute(f"""
        DELETE FROM messages
        WHERE id=%s AND sender_type=%s AND {sender_id_field}=%s
    """, (message_id, sender_type, sender_id_value))
    db.commit()

    flash("✅ Message deleted.")
    return redirect(f'/message_center/{patient_id}')


@app.route('/remove_patient/<int:patient_id>')
def remove_patient(patient_id):
    if 'doctor_id' not in session:
        return redirect('/doctor_login')
    
    doctor_id = session['doctor_id']

    # Remove patient-doctor assignment
    cursor.execute("""
        DELETE FROM patient_doctor 
        WHERE doctor_id=%s AND patient_id=%s
    """, (doctor_id, patient_id))
    db.commit()

    flash("✅ Patient removed successfully.")
    return redirect('/doctor_dashboard')


# Doctor Logout
@app.route('/doctor_logout')
def doctor_logout():
    session.pop('doctor_id', None)
    flash("👋 Doctor logged out successfully.")
    return redirect('/')

# ------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)