from flask import Flask, render_template, request, redirect, flash,session
from werkzeug.security import( generate_password_hash, check_password_hash)
import sqlite3
import csv
import io
from flask import Response
from datetime import datetime
from flask import send_file
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Table
from reportlab.platypus import TableStyle
from reportlab.platypus import Paragraph
from reportlab.platypus import Spacer

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from functools import wraps
import re

import smtplib
from email.message import EmailMessage
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)

class Config:

    SECRET_KEY = os.getenv("SECRET_KEY")
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

app.config.from_object(Config)

app.secret_key = app.config["SECRET_KEY"]

EMAIL_ADDRESS = app.config["EMAIL_ADDRESS"]
EMAIL_PASSWORD = app.config["EMAIL_PASSWORD"]

if not EMAIL_ADDRESS or not EMAIL_PASSWORD:

    raise RuntimeError(
        "EMAIL_ADDRESS or EMAIL_PASSWORD is missing from .env"
    )





if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY is missing from .env"
    )

def connect_db():

    conn = sqlite3.connect('database.db')

    conn.execute("PRAGMA foreign_keys = ON")

    conn.row_factory = sqlite3.Row

    return conn

def log_activity(
    admin_id,
    activity_type,
    description
):

    conn = connect_db()

    created_at = datetime.now().strftime(
        "%d-%m-%Y %H:%M"
    )

    conn.execute(

        """

        INSERT INTO activities
        (
            admin_id,
            activity_type,
            description,
            created_at
        )

        VALUES (?, ?, ?, ?)

        """,

        (
            admin_id,
            activity_type,
            description,
            created_at
        )

    )

    conn.commit()

    conn.close()


def create_tables():

    conn = connect_db()

    # admin table
# Admin table
    conn.execute("""

    CREATE TABLE IF NOT EXISTS admin (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT NOT NULL UNIQUE,

        email TEXT NOT NULL UNIQUE,

        mobile TEXT,

        password TEXT NOT NULL,

        theme TEXT DEFAULT 'light'

    )

    """)

    # students table
    conn.execute("""

    CREATE TABLE IF NOT EXISTS students (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        admin_id INTEGER NOT NULL,

        student_code TEXT NOT NULL UNIQUE,

        name TEXT NOT NULL,

        mobile TEXT NOT NULL,
                 
        email TEXT  NOT NULL,

        hostel TEXT NOT NULL,

        room TEXT NOT NULL,

        department TEXT NOT NULL,

        academic_level TEXT NOT NULL,

        total_fees INTEGER NOT NULL DEFAULT 30000,

        received_amount INTEGER NOT NULL DEFAULT 0,

        joining_date TEXT NOT NULL,

        FOREIGN KEY (admin_id) REFERENCES admin(id),

        UNIQUE(admin_id, mobile),

        CHECK(received_amount >= 0),

        CHECK(total_fees >= 0),

        CHECK(received_amount <= total_fees)

    )

    """)

    # payments table
    conn.execute("""

    CREATE TABLE IF NOT EXISTS payments (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        payment_mode TEXT NOT NULL,
        payment_date TEXT NOT NULL,
        FOREIGN KEY (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,
        CHECK(amount > 0)

    )

    """)

    conn.execute("""

    CREATE TABLE IF NOT EXISTS activities (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        admin_id INTEGER NOT NULL,

        activity_type TEXT NOT NULL,

        description TEXT NOT NULL,

        created_at TEXT NOT NULL

    )

    """)



    # default admin

    admin = conn.execute(

        "SELECT * FROM admin WHERE username = ?",

        ('admin',)

    ).fetchone()


    if not admin:

        hashed_password = generate_password_hash("admin123")

        conn.execute(

            """

            INSERT INTO admin
            (
                username,
                email,
                mobile,
                password,
                theme
            )

            VALUES (?, ?, ?, ?, ?)

            """,

            (

                "admin",

                "admin@gmail.com",

                "9999999999",

                hashed_password,

                "light"

            )

        )





    conn.commit()

    conn.close()

    
create_tables()

def find_admin(identifier):

    identifier = identifier.strip().lower()

    conn = connect_db()

    admin = conn.execute(

        """

        SELECT *

        FROM admin

        WHERE

            LOWER(username)=LOWER(?)

            OR LOWER(email)=LOWER(?)

            OR mobile=?

        """,

        (

            identifier,

            identifier,

            identifier

        )

    ).fetchone()

    conn.close()

    return admin

def send_email(receiver_email, subject, body):

    msg = EmailMessage()

    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = receiver_email

    msg.set_content(body)

    try:

        with smtplib.SMTP("smtp.gmail.com", 587) as server:

            server.starttls()

            server.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            server.send_message(msg)

        return True

    except Exception as e:

        print("Email Error:", e)

        return False

def login_required(func):

    @wraps(func)

    def wrapper(*args, **kwargs):

        if not session.get('admin_logged_in'):

            return redirect('/login')

        return func(*args, **kwargs)

    return wrapper


@app.route("/test_email")
def test_email():

    success = send_email(

        "rchopade422@gmail.com",

        "Mess Manager Test",

        "Congratulations! Your Flask email setup is working successfully."

    )

    if success:
        return "Email sent successfully!"

    else:
        return "Failed to send email."


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        identifier = request.form['identifier'].strip()
        password = request.form['password']

        admin = find_admin(identifier)

        if admin and check_password_hash(admin["password"],password):

            session['admin_logged_in'] = True

            session['admin_id'] = admin['id']

            session['admin_username'] = admin['username']

            session['theme'] = admin['theme']

           

            flash('Login successful!',"success")

            return redirect('/')


        else:

            flash(
                        "Invalid username, email, mobile number, or password.",
                        "error"
                    )

            return redirect('/login')


    return render_template('login.html')

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    print("CHANGE PASSWORD ROUTE HIT")

    current_password = request.form['current_password']

    new_password = request.form['new_password']

    confirm_password = request.form['confirm_password']

    admin_id = session['admin_id']

    conn = connect_db()

    admin = conn.execute(

        """

        SELECT *

        FROM admin

        WHERE id = ?

        """,

        (admin_id,)

    ).fetchone()

    if not check_password_hash(
        admin['password'],
        current_password
    ):

        conn.close()

        flash(
            "Current password is incorrect",
            "error"
        )

        return redirect('/profile')

    if new_password != confirm_password:

    

        conn.close()

        flash(
            "New passwords do not match",
            "error"
        )

        return redirect('/profile')
    
    
    if len(new_password) < 8:

        conn.close()

        flash(
            "Password must be at least 6 characters",
            "error"
        )

        return redirect('/profile')

    hashed_password = generate_password_hash(
        new_password
    )

    conn.execute(

        """

        UPDATE admin

        SET password = ?

        WHERE id = ?

        """,

        (
            hashed_password,
            admin_id
        )

    )

    conn.commit()


    log_activity(

        admin_id,

        "Security",

        "Password changed"

    )

    conn.close()

    flash(
        "Password updated successfully",
        "success"
    )

    return redirect('/profile')

@app.route('/change_password_page')
@login_required
def change_password_page():

    return render_template(
        'change_password.html'
    )

@app.route("/forgot_password")
def forgot_password():

    return render_template("forgot_password.html")

@app.route("/send_otp", methods=["POST"])
def send_otp():

    identifier = request.form["identifier"].strip()
    
    admin = find_admin(identifier)

    if not admin:

        flash(

            "No account found with the provided username, email, or mobile number.",

            "error"

        )
        return redirect("/forgot_password")

    otp = str(random.randint(100000, 999999))


    email = admin["email"]
    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = (
        datetime.now() + timedelta(minutes=5)
    ).isoformat()



    session["resend_available_at"] = (
        datetime.now() + timedelta(seconds=60)
    ).isoformat()

    subject = "Mess Manager Password Reset OTP"

    body = f"""
Hello,

Your OTP for resetting your Mess Manager password is:

{otp}

This OTP is valid for 5 minutes.

If you did not request a password reset, you can ignore this email.

Regards,
Mess Manager
"""

    if send_email(email, subject, body):

        flash("OTP sent successfully to your email.", "success")

        return redirect("/verify_otp")

    else:

        flash("Failed to send OTP. Please try again.", "error")

        return redirect("/forgot_password")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "GET":

        email = session.get("reset_email")

        if not email:

            flash(
                "Please request an OTP first.",
                "error"
            )

            return redirect("/forgot_password")

        name, domain = email.split("@")

        if len(name) > 5:

            masked_email = (
                name[:3]
                + "*" * (len(name) - 5)
                + name[-2:]
                + "@"
                + domain
            )

        else:

            masked_email = name[0] + "***@" + domain

        remaining = 0

        available_at = session.get("resend_available_at")

        if available_at:

            available_time = datetime.fromisoformat(available_at)

            remaining = max(
                0,
                int((available_time - datetime.now()).total_seconds())
            )

        return render_template(

            "verify_otp.html",

            masked_email=masked_email,

            remaining=remaining

        )



    entered_otp = request.form["otp"].strip()

    stored_otp = session.get("reset_otp")

    expiry = session.get("otp_expiry")

    if not stored_otp or not expiry:

        flash(
            "Please request a new OTP.",
            "error"
        )

        return redirect("/forgot_password")

    expiry_time = datetime.fromisoformat(expiry)

    if datetime.now() > expiry_time:

        session.pop("reset_otp", None)
        session.pop("otp_expiry", None)

        flash(
            "OTP has expired. Please request a new one.",
            "error"
        )

        return redirect("/forgot_password")

    if entered_otp != stored_otp:

        flash(
            "Incorrect OTP.",
            "error"
        )

        return redirect("/verify_otp")

    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)

    flash(
        "OTP verified successfully.",
        "success"
    )

    return redirect("/reset_password")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if "reset_email" not in session:

        flash(
            "Please verify OTP first.",
            "error"
        )

        return redirect("/forgot_password")

    if request.method == "GET":

        return render_template(
            "reset_password.html"
        )

    new_password = request.form["new_password"]

    confirm_password = request.form["confirm_password"]

    if new_password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return redirect("/reset_password")

    if len(new_password) < 8:

        flash(
            "Password must be at least 8 characters.",
            "error"
        )

        return redirect("/reset_password")

    hashed_password = generate_password_hash(
        new_password
    )

    conn = connect_db()

    conn.execute(

        """

        UPDATE admin

        SET password = ?

        WHERE email = ?

        """,

        (

            hashed_password,

            session["reset_email"]

        )

    )

    conn.commit()

    conn.close()

    session.pop("reset_email", None)

    flash(

        "Password reset successfully. Please login.",

        "success"

    )

    return redirect("/login")


@app.route("/signup", methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username'].strip()

        password = request.form['password']

        email = request.form["email"].strip().lower()

        mobile = request.form["mobile"].strip()

        confirm_password = request.form['confirm_password']

        # Password strength validation

        if len(password) < 8:

            flash("Password must be at least 8 characters","error")

            return redirect('/signup')


        if not re.search(r"[A-Za-z]", password):

            flash("Password must contain letters","error")

            return redirect('/signup')


        if not re.search(r"[0-9]", password):

            flash("Password must contain numbers","error")

            return redirect('/signup')



        # Password match validation

        if password != confirm_password:

            flash("Passwords do not match","error")

            return redirect('/signup')


        conn = connect_db()

        # Username validation

        if len(username) < 4:

            flash("Username must be at least 4 characters")

            return redirect('/signup')


        if not re.match(r"^[A-Za-z0-9_]+$", username):

            flash("Username can only contain letters, numbers and underscore")

            return redirect('/signup')


        # Check duplicate username

        existing_admin = conn.execute(

            """

            SELECT *

            FROM admin

            WHERE LOWER(username)=LOWER(?)

            """,

            (username,)

        ).fetchone()
        
        if existing_admin:

            conn.close()

            flash("Username already exists", "error")

            return redirect("/signup")
        
        existing_mobile = conn.execute(

            """

            SELECT *

            FROM admin

            WHERE mobile = ?

            """,

            (mobile,)

        ).fetchone()

        if existing_mobile:

            conn.close()

            flash("Mobile number already registered", "error")

            return redirect("/signup")

        # email varifications

        existing_email = conn.execute(

            "SELECT * FROM admin WHERE email = ?",

            (email,)

        ).fetchone()

        if existing_email:

            conn.close()

            flash("Email already registered", "error")

            return redirect("/signup")



        # Create admin account

        hashed_password = generate_password_hash(password)

        conn.execute(

            """

            INSERT INTO admin(
                username,
                email,
                mobile,
                password,
                theme
            )
            VALUES (?, ?, ?, ?, ?)

            """,

                (
                    username,
                    email,
                    mobile,
                    hashed_password,
                    "light"
                )

        )

        conn.commit()

        conn.close()


        flash("Account created successfully!","success")

        return redirect("/login")


    return render_template("signup.html")

@app.route("/resend_otp")
def resend_otp():

    available_at = session.get("resend_available_at")

    if available_at:

        available_time = datetime.fromisoformat(available_at)

        if datetime.now() < available_time:

            remaining = int(
                (available_time - datetime.now()).total_seconds()
            )

            flash(
                f"Please wait {remaining} seconds before requesting another OTP.",
                "error"
            )

            return redirect("/verify_otp")

    session["resend_available_at"] = (
        datetime.now() + timedelta(seconds=60)
    ).isoformat()


    email = session.get("reset_email")

    if not email:

        flash(
            "Please start the password reset process again.",
            "error"
        )

        return redirect("/forgot_password")

    otp = str(random.randint(100000, 999999))

    session["reset_otp"] = otp

    session["otp_expiry"] = (
        datetime.now() + timedelta(minutes=5)
    ).isoformat()

    subject = "Mess Manager Password Reset OTP"

    body = f"""
Hello,

Your new OTP is:

{otp}

This OTP is valid for 5 minutes.

Regards,
Mess Manager
"""

    if send_email(email, subject, body):

        flash(
            "A new OTP has been sent.",
            "success"
        )

    else:

        flash(
            "Unable to send OTP.",
            "error"
        )

    return redirect("/verify_otp")

@app.route('/set_theme', methods=['POST'])
@login_required
def set_theme():

    theme = request.form['theme']

    admin_id = session['admin_id']

    conn = connect_db()

    conn.execute(

        """
        UPDATE admin
        SET theme = ?
        WHERE id = ?
        """,

        (theme, admin_id)

    )

    conn.commit()
    conn.close()

    session['theme'] = theme

    return redirect('/profile')

@app.route('/profile')
@login_required
def profile():

    admin_username = session['admin_username']
    current_theme = session.get('theme', 'light')
    return render_template(

        'profile.html',

        admin_username=admin_username,
        current_theme=current_theme

    )

@app.route('/logout')
def logout():

    session.clear()

    flash('Logged out successfully!',"success")

    return redirect('/login')

@app.route('/activities')
@login_required
def activities():

    conn = connect_db()

    admin_id = session['admin_id']

    activities = conn.execute(

        """

        SELECT

            activity_type,

            description,

            created_at

        FROM activities

        WHERE admin_id = ?

        ORDER BY id DESC

        """,

        (admin_id,)

    ).fetchall()

    conn.close()

    return render_template(

        "activities.html",

        activities=activities

    )

@app.route('/')
@login_required
def home():

    conn = connect_db()

    admin_id = session['admin_id']

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students WHERE admin_id = ?"
    ,
    (admin_id,)
    ).fetchone()[0]

    total_collected = conn.execute(
        "SELECT SUM(received_amount) FROM students WHERE admin_id = ?"
    ,
    (admin_id,)
    ).fetchone()[0]

    recent_activities = conn.execute(

        """

        SELECT
            activity_type,
            description,
            created_at

        FROM activities

        WHERE admin_id = ?

        ORDER BY id DESC

        LIMIT 5

        """,

        (admin_id,)

    ).fetchall()


    print("ACTIVITIES:", len(recent_activities))

    for activity in recent_activities:
        print(dict(activity))

    total_pending = conn.execute(

        """

        SELECT SUM(total_fees - received_amount)

        FROM students

        WHERE admin_id = ?

        """,

        (admin_id,)

    ).fetchone()[0]

    pending_students = conn.execute(

        """

        SELECT COUNT(*)

        FROM students

        WHERE admin_id = ?

        AND (total_fees - received_amount) > 0

        """,

        (admin_id,)

    ).fetchone()[0]


    total_fees = conn.execute(

        """

        SELECT SUM(total_fees)

        FROM students

        WHERE admin_id = ?

        """,

        (admin_id,)

    ).fetchone()[0]

    if total_fees is None:
        total_fees = 0
        
    conn.close()

    if total_collected is None:
        total_collected = 0

    if total_pending is None:
        total_pending = 0


    if total_fees > 0:
        collection_percentage = round(
            (total_collected / total_fees) * 100
        )

    else:
        collection_percentage = 0


    if collection_percentage < 30:

        progress_color = "#dc2626"   # Red

    elif collection_percentage < 70:

        progress_color = "#f59e0b"   # Orange

    else:

        progress_color = "#16a34a"   # Green

    return render_template(
        "home.html",
        total_students=total_students,
        total_collected=total_collected,
        total_pending=total_pending,
        pending_students=pending_students,
        recent_activities=recent_activities,
        collection_percentage=collection_percentage,
        total_fees=total_fees,
        progress_color=progress_color
    )

@app.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):

    conn = connect_db()

    admin_id = session['admin_id']

    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized delete attempt","error")

        return redirect('/student_list')

    student_name = student['name']

    conn.execute(
        "DELETE FROM payments WHERE student_id=?",
        (student_id,)
    )

    conn.execute(

        "DELETE FROM students WHERE id=? AND admin_id=?",

        (student_id, admin_id)

    )

    conn.commit()

    log_activity(

        admin_id,

        "Delete",

        f"Deleted student {student_name}"

    )

    conn.close()

    flash("Student deleted successfully!","success")

    return redirect('/student_list')


@app.route('/import_students', methods=['GET', 'POST'])
@login_required
def import_students():

    if request.method == 'POST':

        print("POST RECEIVED")

        csv_file = request.files['csv_file']

        if not csv_file:

            flash(
                "Please select a CSV file",
                "error"
            )

            return redirect('/import_students')

        csv_data = csv_file.read().decode('utf-8')

        reader = csv.DictReader(
            io.StringIO(csv_data)
        )

        total_rows = 0
        valid_rows = 0
        invalid_rows = 0

        conn = connect_db()
        admin_id = session['admin_id']

        invalid_details = []
        valid_students = []


        for row_number, row in enumerate(reader, start=2):
            total_rows += 1

            name = row.get("Name", "").strip()
            mobile = row.get("Mobile", "").strip()
            hostel = row.get("Hostel", "").strip()
            room = row.get("Room", "").strip()
            department = row.get("Department", "").strip()
            academic_level = row.get("Academic Level", "").strip()
            email = row.get("Email", "").strip()

            if not all([
                name,
                mobile,
                hostel,
                room,
                department,
                academic_level
            ]):

                invalid_rows += 1

                invalid_details.append(
                    f"Row {row_number}: Missing required fields"
                )

                continue

            if not mobile.isdigit() or len(mobile) != 10:
                invalid_rows += 1

                invalid_details.append(
                    f"Row {row_number}: Invalid mobile number"
                )

                continue


            existing_student = conn.execute(

                """
                SELECT id
                FROM students
                WHERE mobile = ?
                AND admin_id = ?
                """,

                (mobile, admin_id)

            ).fetchone()

            if existing_student:

                invalid_rows += 1

                invalid_details.append(
                    f"Row {row_number}: {name} already exists"
                )

                continue


            if email and not re.match(
                r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
                email
            ):

                invalid_rows += 1

                invalid_details.append(
                    f"Row {row_number}: Invalid email"
                )

                continue

            valid_rows += 1

            valid_students.append({

                "name": name,

                "mobile": mobile,

                "email": email,

                "hostel": hostel,

                "room": room,

                "department": department,

                "academic_level": academic_level

            })

        session['valid_students'] = valid_students

        conn.close()

        print(
            total_rows,
            valid_rows,
            invalid_rows,
            invalid_details
        )

        return render_template(

            "import_students.html",

            total_rows=total_rows,

            valid_rows=valid_rows,

            invalid_rows=invalid_rows,

            invalid_details=invalid_details

        )

    return render_template(
        "import_students.html"
    )

@app.route('/confirm_import', methods=['POST'])
@login_required
def confirm_import():

    valid_students = session.get(
        'valid_students',
        []
    )

    if not valid_students:

        flash(
            "No validated students found",
            "error"
        )

        return redirect('/import_students')

    conn = connect_db()

    admin_id = session['admin_id']

    imported_count = 0

    for student in valid_students:

        student_count = conn.execute(

            """

            SELECT COUNT(*)

            FROM students

            WHERE admin_id = ?

            """,

            (admin_id,)

        ).fetchone()[0]

        student_code = f"MM{student_count + 1:03}"

        print(
            student['name'],
            student_code
        )

        joining_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

        conn.execute(

            """

            INSERT INTO students
            (

                admin_id,

                student_code,

                name,

                mobile,

                email,

                hostel,

                room,

                department,

                academic_level,

                total_fees,

                received_amount,

                joining_date

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (

                admin_id,

                student_code,

                student['name'],

                student['mobile'],

                student['email'],

                student['hostel'],

                student['room'],

                student['department'],

                student['academic_level'],

                30000,

                0,

                joining_date

            )

        )

        imported_count += 1

    conn.commit()

    log_activity(

        admin_id,

        "Import",

        f"Imported {imported_count} students"

    )

    conn.close()

    session.pop(
        'valid_students',
        None
    )

    flash(
        f"{imported_count} students imported successfully!",
        "success"
    )

    return redirect(
        '/student_list'
    )



@app.route('/add_student_page')
@login_required
def add_student_page():
    return render_template("add_student.html")


@app.route('/student_list')
@login_required
def student_list():
    search = request.args.get('search')

    hostel = request.args.get('hostel')
    print(hostel)
    conn = connect_db()

    
    admin_id = session['admin_id']

    # BOTH hostel + search

    if hostel and search:

        students = conn.execute(

            """

            SELECT * FROM students

            WHERE admin_id =? 
            
            AND hostel = ?

            AND (

                name LIKE ?

                OR room LIKE ?

                OR mobile LIKE ?

            )

            """,

            (
                admin_id,

                hostel,

                f"%{search}%",

                f"%{search}%",

                f"%{search}%"

            )

        ).fetchall()


    # ONLY hostel filter

    elif hostel:

        students = conn.execute(

            "SELECT * FROM students WHERE admin_id = ? AND hostel = ?",

            (admin_id,hostel)

        ).fetchall()


    # ONLY search

    elif search:

        students = conn.execute(

            """

            SELECT * FROM students

            WHERE admin_id = ?

            AND  (

                name LIKE ?

                OR room LIKE ?

                OR mobile LIKE ?

                )

            """,

            (
                admin_id,
                f"{search}%",
                f"{search}%",
                f"{search}%"

            )

        ).fetchall()
        

    # NO filters

    else:

        students = conn.execute(

            """
            SELECT * FROM students 
            WHERE admin_id = ?

            """

        ,

        (admin_id,)

        ).fetchall()


    conn.close()

    return render_template(

        "student_list.html",

        students=students,

        hostel=hostel
)


@app.route('/payment_page')
@login_required
def payment_page():
    conn = connect_db() 
    students = conn.execute(

        """

        SELECT
            id,
            name,
            (total_fees - received_amount) AS remaining_amount

        FROM students

        """

    ).fetchall()



    conn.close()

    return render_template("payment.html", students=students)


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':

        name = request.form['name'].strip()
        room = request.form['room'].strip()
        hostel = request.form['hostel'].strip()
        department = request.form['department'].strip()
        mobile = request.form['mobile'].strip()
        email = request.form['email'].strip()

        if not mobile.isdigit() or len(mobile) != 10:

            flash("Mobile number must be exactly 10 digits","error")

            return redirect(request.url)
        
        if email and not re.match(

            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",

            email

        ):

            flash("Enter a valid email address", "error")

            return redirect(request.url)
        
        
        academic_level = request.form['academic_level'].strip()
        admin_id = session['admin_id']

        conn = connect_db()

        student_count = conn.execute(

            """

            SELECT COUNT(*)

            FROM students

            WHERE admin_id = ?

            """,

            (admin_id,)

        ).fetchone()[0]


        student_code = f"MM{student_count + 1:03}"
        total_fees = 30000

        

        
        joining_date = datetime.now().strftime("%d-%m-%Y")
        
        existing_student = conn.execute(

            """

            SELECT *

            FROM students

            WHERE mobile = ?

            AND admin_id = ?

            """,

            (mobile, admin_id)

        ).fetchone()


        if existing_student:

            conn.close()

            flash("Student with this mobile already exists","error")

            return redirect('/add_student')
        
        conn.execute(

            """

            INSERT INTO students
            (

                admin_id,

                student_code,

                name,

                mobile,

                email,

                hostel,

                room,

                department,

                academic_level,

                total_fees,

                received_amount,

                joining_date

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (

                admin_id,

                student_code,

                name,

                mobile,

                email,

                hostel,

                room,

                department,

                academic_level,

                total_fees,

                0,

                joining_date

            )

        )
        conn.commit()

        log_activity(

            admin_id,

            "Student",

            f"Added student {name}"

        )

        conn.close()

        flash("Student added successfully!","success")

        return redirect('/student_list')

    return render_template('add_student.html')





@app.route('/payment_history/<int:student_id>')
@login_required
def payment_history(student_id):
    conn = connect_db()
    admin_id = session['admin_id']

    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()
    
    if not student:

        conn.close()

        flash("Unauthorized access")

        return redirect('/student_list')

    history = conn.execute(
        "SELECT amount, payment_date FROM payments WHERE student_id = ? ORDER BY payment_date DESC",
        (student_id,)
    ).fetchall()

    conn.close()

    return render_template("payment_history.html", history=history)


@app.route('/receive_payment', methods=['POST'])
@login_required
def receive_payment():


    student_id = request.form['student_id']

    amount = int(request.form['amount'])

    payment_mode = request.form['payment_mode']

    conn = connect_db()

    admin_id = session['admin_id']

    # Prevent zero or negative payment

    if amount <= 0:

        flash("Payment amount must be greater than 0","error")

        conn.close()

        return redirect(f'/student_profile/{student_id}')


    # Get current student data

    student = conn.execute(

        """

        SELECT
            name,
            received_amount,
            total_fees
        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id,admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized payment attempt","error")

        return redirect('/student_list')

    current_received = student['received_amount']

    current_remaining = student['total_fees'] - student['received_amount']


    # Prevent overpayment

    if amount > current_remaining:

        flash("Payment exceeds remaining amount","error")

        conn.close()

        return redirect(f'/student_profile/{student_id}')


    # Calculate updated values

    new_received = current_received + amount

    # Update student table

    conn.execute(

        """

        UPDATE students

        SET received_amount = ?

        WHERE id = ?
        
        AND admin_id=?

        """,

        (new_received, student_id, admin_id)

    )


    # Store payment history
    payment_date = datetime.now().strftime("%d-%m-%Y %H:%M")


    conn.execute(

        """

        INSERT INTO payments
        (
            student_id,
            amount,
            payment_mode,
            payment_date
        )

        VALUES (?, ?, ?, ?)


        """,

        (student_id, amount, payment_mode ,payment_date)

    )



    conn.commit()

    log_activity(

        admin_id,

        "Payment",

        f"{student['name']} paid ₹{amount} via {payment_mode}"

    )

    conn.close()


    flash("Payment received successfully!","success")

    return redirect(f'/student_profile/{student_id}')


@app.route('/edit_student/<int:student_id>')
@login_required
def edit_student(student_id):
 

    conn = connect_db()
    admin_id = session['admin_id']

    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized access")

        return redirect('/student_list')

    conn.close()

    return render_template("edit_student.html", student=student)


@app.route('/update_student', methods=['POST'])
@login_required
def update_student():
 

    student_id = request.form['student_id'].strip()
    name = request.form['name'].strip()
    room = request.form['room'].strip()
    hostel = request.form['hostel'].strip()
    mobile = request.form['mobile'].strip()
    email = request.form['email'].strip()
    department = request.form['department'].strip()
    academic_level = request.form['academic_level'].strip()

    conn = connect_db()
    admin_id = session['admin_id']
    
    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized update attempt","error")

        return redirect('/student_list')
    

    # Mobile validation

    if not re.match(r"^[0-9]{10}$", mobile):

        flash("Mobile number must contain exactly 10 digits")

        conn.close()

        return redirect(f'/edit_student/{student_id}')
    
    if email and not re.match(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
        email
    ):
        flash("Enter a valid email address", "error")
        conn.close()
        return redirect(f'/edit_student/{student_id}')
    
    # Duplicate mobile validation

    existing_mobile = conn.execute(

        """

        SELECT *

        FROM students

        WHERE mobile = ?

        AND id != ?

        AND admin_id = ?

        """,

        (mobile, student_id, admin_id)

    ).fetchone()

    if existing_mobile:

        conn.close()

        flash("Mobile number already exists","error")

        return redirect(f'/edit_student/{student_id}')

    conn.execute(
        """
        UPDATE students

        SET
        name=?,
        room=?,
        hostel=?,
        mobile=?,
        email=?,
        department=?,
        academic_level=?
        WHERE id=?
        AND admin_id=?
        """,

        (
            name,
            room,
            hostel,
            mobile,
            email,
            department,
            academic_level,
            student_id,
            admin_id
        )
    )

    conn.commit()

    log_activity(

        admin_id,

        "Edit",

        f"Updated student {name}"

    )

    conn.close()

    flash("Student updated successfully!","success")

    return redirect('/student_list')


@app.route("/student_profile/<int:student_id>")
@login_required
def student_profile(student_id):
 

    conn = connect_db()
    admin_id = session['admin_id']

    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized access")

        return redirect('/student_list')

    payments = conn.execute(

    """

    SELECT
        amount,
        payment_mode,
        payment_date


    FROM payments

    WHERE student_id = ?

    ORDER BY payment_date DESC

    """,

    (student_id,)

).fetchall()

    conn.close()

    name = student["name"]

    initials = "".join(
        word[0].upper()
        for word in name.split()[:2]
    )

    return render_template(
        "student_profile.html",
        student=student,
        payments=payments,
        initials=initials
    )


@app.route('/receive_payment_page/<int:student_id>')
@login_required
def receive_payment_page(student_id):

    conn = connect_db()

    admin_id = session['admin_id']

    student = conn.execute(

        """

        SELECT *

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id, admin_id)

    ).fetchone()


    if not student:

        conn.close()

        flash("Unauthorized access","error")

        return redirect('/student_list')


    conn.close()


    name = student["name"]

    initials = "".join(
        word[0].upper()
        for word in name.split()[:2]
    )

    return render_template(

        "receive_payment.html",

        student=student,
        initials=initials

    )

@app.route("/pending_payments")
@login_required
def pending_payments():
 

    conn = connect_db()
    admin_id = session['admin_id']
    payment_filter = request.args.get('payment_filter')

    if payment_filter == "1_5000":

        students = conn.execute(

            """

            SELECT *

            FROM students

            WHERE admin_id = ?

            AND (total_fees - received_amount) > 0
            AND (total_fees - received_amount) <= 5000

            ORDER BY (total_fees - received_amount) ASC

            """,

            (admin_id,)

        ).fetchall()


    elif payment_filter == "1_15000":

        students = conn.execute(

            """

            SELECT *

            FROM students

            WHERE admin_id = ?

            
            AND (total_fees - received_amount) > 0
            AND (total_fees - received_amount) <= 15000

            ORDER BY (total_fees - received_amount) DESC

            """,

            (admin_id,)

        ).fetchall()


    elif payment_filter == "15000":

        students = conn.execute(

            """

            SELECT *

            FROM students

            WHERE admin_id = ?

            AND (total_fees - received_amount) > 15000

            ORDER BY (total_fees - received_amount) DESC

            """,

            (admin_id,)

        ).fetchall()


    else:

        students = conn.execute(

            """

            SELECT *

            FROM students

            WHERE admin_id = ?

            AND (total_fees - received_amount) > 0

            ORDER BY (total_fees - received_amount) DESC

            """,

            (admin_id,)

        ).fetchall()
    conn.close()

    return render_template(
        "pending_payments.html",
        students=students
    )


@app.route('/download_pending_pdf')
@login_required
def download_pending_pdf():
 

    conn = connect_db()
    admin_id = session['admin_id']

    students = conn.execute(

        """

       SELECT
            name,
            hostel,
            (total_fees - received_amount) AS remaining_amount

        FROM students

        WHERE admin_id = ?

        AND (total_fees - received_amount) > 0

        ORDER BY (total_fees - received_amount) DESC

        """,

        (admin_id,)

    ).fetchall()

    conn.close()

    pdf_file = "pending_payments_report.pdf"

    doc = SimpleDocTemplate(pdf_file)

    elements = []

    styles = getSampleStyleSheet()

    title = Paragraph(
        "Pending Payments Report",
        styles['Title']
    )

    elements.append(title)

    elements.append(Spacer(1, 20))

    # table data
    data = [
        ["Sr No", "Name", "Hostel", "Remaining Amount"]
    ]

    total_pending = 0

    for index, student in enumerate(students, start=1):

        data.append([
            index,
            student[0],
            student[1],
            f"Rs. {student[2]}"
        ])

        total_pending += student[2]

    # total row
    data.append([
        "",
        "",
        "Total Pending",
        f"Rs. {total_pending}"
    ])

    table = Table(data, colWidths=[60, 180, 140, 140])

    table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.grey),

        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),

        ('ALIGN', (0,0), (-1,-1), 'CENTER'),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0,0), (-1,0), 12),

        ('BACKGROUND', (0,1), (-1,-2), colors.beige),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),

        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey)

    ]))

    elements.append(table)

    doc.build(elements)

    return send_file(
        pdf_file,
        as_attachment=True
    )


@app.route('/download_students_pdf')
@login_required
def download_students_pdf():
 

    conn = connect_db()
    admin_id = session['admin_id']

    students = conn.execute(

        """

        SELECT
            name,
            hostel,
            room,
            (total_fees - received_amount) AS remaining_amount

        FROM students

        WHERE admin_id = ?

        ORDER BY name

        """,

        (admin_id,)

    ).fetchall()
    conn.close()

    pdf_file = "students_report.pdf"

    doc = SimpleDocTemplate(pdf_file)

    elements = []

    styles = getSampleStyleSheet()

    title = Paragraph(
        "Students Report",
        styles['Title']
    )

    elements.append(title)

    elements.append(Spacer(1, 20))

    data = [
        ["Sr No", "Name", "Hostel", "Room", "Remaining"]
    ]

    total_pending = 0

    for index, student in enumerate(students, start=1):

        data.append([
            index,
            student[0],
            student[1],
            student[2],
            f"Rs. {student[3]}"
        ])

        total_pending += student[3]

    data.append([
        "",
        "",
        "",
        "Total Pending",
        f"Rs. {total_pending}"
    ])

    table = Table(
        data,
        colWidths=[50, 180, 140, 100, 120]
    )

    table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.grey),

        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),

        ('ALIGN', (0,0), (-1,-1), 'CENTER'),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0,0), (-1,0), 12),

        ('BACKGROUND', (0,1), (-1,-2), colors.beige),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),

        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey)

    ]))

    elements.append(table)

    doc.build(elements)

    return send_file(
        pdf_file,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=True)