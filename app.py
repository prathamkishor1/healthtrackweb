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

# Landing Page Route (Project Intro)
@app.route('/')
def index():
    return render_template('index.html')

# Login Page Route
@app.route('/login')
def login_page():
    return render_template('login.html')

# Registration Page Route
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

# Login Logic Route (POST)
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

# Dashboard Route with AI Suggestions
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

    return render_template('dashboard.html', logs=logs, data=logs, user_name=user_name, averages=averages, suggestions=suggestions)

# Add Health Log with AI alerts
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

# Delete Individual Log
@app.route('/delete_log/<int:log_id>')
def delete_log(log_id):
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("DELETE FROM health_logs WHERE id=%s", (log_id,))
    db.commit()
    flash("✅ Health log deleted successfully.")
    return redirect('/dashboard')

# Clear All Logs for user
@app.route('/clear_logs')
def clear_logs():
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("DELETE FROM health_logs WHERE user_id=%s", (session['user_id'],))
    db.commit()
    flash("✅ All logs cleared successfully.")
    return redirect('/dashboard')

# Generate PDF Report
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

# Download CSV Report
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

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Run App
if __name__ == '__main__':
    app.run(debug=True)
