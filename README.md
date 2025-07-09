# 🩺 HealthTrack Web

A simple health monitoring and doctor-patient messaging platform built with **Python (Flask)** and **MySQL**. Patients can log vital health data, download reports, and chat with assigned doctors, while doctors can track patient logs and reply via messages.

---

## 📌 Features

### 👤 Patient Features:
- Register and login securely.
- Log health metrics: temperature, BP, SpO2, blood sugar, notes.
- View health trends (charts) and averages.
- Download health reports as **PDF** and **CSV**.
- Clear individual or all health logs.
- Assign a doctor to begin two-way messaging.
- Send and receive messages with doctor.
- Delete received messages from the dashboard.

### 👨‍⚕️ Doctor Features:
- Doctor registration and login.
- View assigned patients and their health logs.
- Send messages to individual patients.
- View full message history with each patient.
- Remove patient assignment if needed.
- Logout securely.

---

## 🛠️ Tech Stack

- **Python 3.x**
- **Flask**
- **MySQL**
- **WeasyPrint** (for PDF generation)
- **Chart.js** (for health data visualization)
- **SweetAlert2** (for elegant confirmation popups)

---

## 📦 Project Structure

HealthTrackWeb/
├── app.py
├── config.py
├── /templates/
│ ├── index.html
│ ├── login.html
│ ├── register.html
│ ├── dashboard.html
│ ├── doctor_login.html
│ ├── doctor_register.html
│ ├── doctor_dashboard.html
│ ├── assign_doctor.html
│ ├── view_patient.html
│ ├── messages.html
│ ├── message_center.html
│ ├── report.html
├── /static/
│ └── (optional: for custom CSS or images)
├── /venv/
└── requirements.txt (optional)

yaml
Copy
Edit

---

## ⚙️ Setup Instructions

1. **Clone this repository** (if using Git)
   ```bash
   git clone <repo-url>
   cd HealthTrackWeb
Create a virtual environment

bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
If requirements.txt isn't available, install manually:

bash
Copy
Edit
pip install Flask mysql-connector-python weasyprint chart.js sweetalert2
Configure database

Create a MySQL database and import your tables:

users

doctors

health_logs

messages

patient_doctor

Update config.py with your MySQL credentials:

python
Copy
Edit
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'healthtrack'
}
Run the app

bash
Copy
Edit
python app.py
Visit: http://127.0.0.1:5000/

