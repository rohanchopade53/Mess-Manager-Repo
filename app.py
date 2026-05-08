from flask import Flask, render_template, request, redirect, flash,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import csv
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


app = Flask(__name__)
app.secret_key = 'messmanagersecretkey'

def connect_db():
    return sqlite3.connect("database.db")


def create_tables():
    conn = connect_db()

    # students table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        room TEXT,
        hostel TEXT,
        received_amount INTEGER DEFAULT 0,
        remaining_amount INTEGER DEFAULT 30000
    )
    """)

    # admin table

    conn.execute("""

    CREATE TABLE IF NOT EXISTS admin(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE,

        password TEXT

    )

    """)

    # default admin

    admin = conn.execute(

        "SELECT * FROM admin WHERE username = ?",

        ('admin',)

    ).fetchone()


    if not admin:

        conn.execute(

            "INSERT INTO admin (username, password) VALUES (?, ?)",

            ('admin', 'admin123')

        )

    # payments table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


    # add admin_id column

    try:

        conn.execute(

            "ALTER TABLE students ADD COLUMN admin_id INTEGER"

        )

    except:

        pass

    
    # add joining_date column if not exists
    try:
        conn.execute(
            "ALTER TABLE students ADD COLUMN joining_date TEXT"
        )
    except:
        pass

    # add department column
    try:
        conn.execute(
            "ALTER TABLE students ADD COLUMN department TEXT"
        )
    except:
        pass

    # add mobile column
    try:
        conn.execute(
            "ALTER TABLE students ADD COLUMN mobile TEXT"
        )
    except:
        pass

    # add academic_level column
    try:
        conn.execute(
            "ALTER TABLE students ADD COLUMN academic_level TEXT"
        )
    except:
        pass

    conn.commit()
    conn.close()


create_tables()


def login_required():

    if 'admin_logged_in' not in session:

        return redirect('/login')
    

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        conn = connect_db()

        admin = conn.execute(

            """

            SELECT *

            FROM admin

            WHERE username = ?

            """,

            (username,)

        ).fetchone()

        conn.close()


        if admin and check_password_hash(admin[2], password):

            session['admin_logged_in'] = True

            session['admin_id'] = admin[0]

            session['admin_username'] = admin[1]

            flash('Login successful!')

            return redirect('/')


        else:

            flash('Invalid username or password')

            return redirect('/login')


    return render_template('login.html')


@app.route("/signup", methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']

        confirm_password = request.form['confirm_password']


        # Password match validation

        if password != confirm_password:

            flash("Passwords do not match")

            return redirect('/signup')


        conn = connect_db()


        # Check duplicate username

        existing_admin = conn.execute(

            "SELECT * FROM admin WHERE username = ?",

            (username,)

        ).fetchone()


        if existing_admin:

            conn.close()

            flash("Username already exists")

            return redirect('/signup')


        # Create admin account

        hashed_password = generate_password_hash(password)

        conn.execute(

            """

            INSERT INTO admin (username, password)

            VALUES (?, ?)

            """,

            (username, hashed_password)

        )

        conn.commit()

        conn.close()


        flash("Account created successfully!")

        return redirect("/login")


    return render_template("signup.html")


@app.route('/logout')
def logout():

    session.pop('admin_logged_in', None)

    flash('Logged out successfully!')

    return redirect('/login')


@app.route('/')
def home():

    check = login_required()

    if check:

        return check

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

    total_pending = conn.execute(
        "SELECT SUM(remaining_amount) FROM students WHERE admin_id = ?"
    ,
    (admin_id,)
    ).fetchone()[0]

    pending_students = conn.execute(

        """

        SELECT COUNT(*)

        FROM students

        WHERE admin_id = ?

        AND remaining_amount > 0

        """,

        (admin_id,)

    ).fetchone()[0]
    

    recent_payments = conn.execute(

        """

        SELECT students.name,

            payments.amount,

            payments.date

        FROM payments

        JOIN students

        ON payments.student_id = students.id

        WHERE students.admin_id = ?

        ORDER BY payments.id DESC

        LIMIT 5

        """,

        (admin_id,)

    ).fetchall()


    conn.close()

    if total_collected is None:
        total_collected = 0

    if total_pending is None:
        total_pending = 0

    return render_template(
        "home.html",
        total_students=total_students,
        total_collected=total_collected,
        total_pending=total_pending,
        pending_students=pending_students,

        recent_payments=recent_payments
    )


@app.route('/add_student_page')
def add_student_page():
    check = login_required()

    if check:

         return check
    return render_template("add_student.html")


@app.route('/student_list')
def student_list():
    check = login_required()

    if check:

         return check

    search = request.args.get('search')

    hostel = request.args.get('hostel')

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

        students=students

    )


@app.route('/payment_page')
def payment_page():
    check = login_required()

    if check:

        return check

    conn = connect_db()

    students = conn.execute(
        "SELECT id, name, remaining_amount FROM students"
    ).fetchall()

    conn.close()

    return render_template("payment.html", students=students)


@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    check = login_required()

    if check:

        return check

    if request.method == 'POST':

        name = request.form['name']
        room = request.form['room']
        hostel = request.form['hostel']
        admin_id = session['admin_id']

        conn = connect_db()

        conn.execute(
            """
            INSERT INTO students
            (name, room, hostel,admin_id)
            VALUES (?, ?, ?, ?)
            """,
            (name, room, hostel, admin_id)
        )

        conn.commit()
        conn.close()

        flash("Student added successfully!")

        return redirect('/student_list')

    return render_template('add_student.html')


@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    check = login_required()

    if check:

        return check

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

        flash("Unauthorized delete attempt")

        return redirect('/student_list')

    # delete payment history first
    conn.execute(
        "DELETE FROM payments WHERE student_id=?",
        (student_id,)
    )

    # delete student
    conn.execute(
        "DELETE FROM students WHERE id=?",
        (student_id,)
    )

    conn.commit()

    conn.close()

    flash("Student deleted successfully!")

    return redirect('/student_list')


@app.route('/payment_history/<int:student_id>')
def payment_history(student_id):
    check = login_required()

    if check:

        return check

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
        "SELECT amount, date FROM payments WHERE student_id = ? ORDER BY date DESC",
        (student_id,)
    ).fetchall()

    conn.close()

    return render_template("payment_history.html", history=history)


@app.route('/receive_payment', methods=['POST'])
def receive_payment():
    check = login_required()

    if check:

        return check

    student_id = request.form['student_id']

    amount = int(request.form['amount'])

    conn = connect_db()
    admin_id = session['admin_id']


    # Prevent zero or negative payment

    if amount <= 0:

        flash("Payment amount must be greater than 0")

        conn.close()

        return redirect(f'/student_profile/{student_id}')


    # Get current student data

    student = conn.execute(

        """

        SELECT received_amount,

            remaining_amount

        FROM students

        WHERE id = ?

        AND admin_id = ?

        """,

        (student_id,admin_id)

    ).fetchone()

    if not student:

        conn.close()

        flash("Unauthorized payment attempt")

        return redirect('/student_list')

    current_received = student[0]

    current_remaining = student[1]


    # Prevent overpayment

    if amount > current_remaining:

        flash("Payment exceeds remaining amount")

        conn.close()

        return redirect(f'/student_profile/{student_id}')


    # Calculate updated values

    new_received = current_received + amount

    new_remaining = current_remaining - amount


    # Update student table

    conn.execute(

        """

        UPDATE students

        SET received_amount = ?,

            remaining_amount = ?

        WHERE id = ?

        """,

        (new_received, new_remaining, student_id)

    )


    # Store payment history

    conn.execute(

        """

        INSERT INTO payments (student_id, amount)

        VALUES (?, ?)

        """,

        (student_id, amount)

    )


    conn.commit()

    conn.close()


    flash("Payment received successfully!")

    return redirect(f'/student_profile/{student_id}')



@app.route('/edit_student/<int:student_id>')
def edit_student(student_id):
    check = login_required()

    if check:

        return check

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
def update_student():
    check = login_required()

    if check:

        return check

    student_id = request.form['student_id']
    name = request.form['name']
    room = request.form['room']
    hostel = request.form['hostel']
    mobile = request.form['mobile']
    department = request.form['department']
    academic_level = request.form['academic_level']

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

        flash("Unauthorized update attempt")

        return redirect('/student_list')

    conn.execute(
        """
        UPDATE students

        SET
        name=?,
        room=?,
        hostel=?,
        mobile=?,
        department=?,
        academic_level=?
        admin_id=?

        WHERE id=?
        AND admin_id=?
        """,

        (
            name,
            room,
            hostel,
            mobile,
            department,
            academic_level,
            student_id
        )
    )

    conn.commit()
    conn.close()

    flash("Student updated successfully!")

    return redirect('/student_list')


@app.route("/student_profile/<int:student_id>")
def student_profile(student_id):
    check = login_required()

    if check:

        return check

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
        "SELECT amount, date FROM payments WHERE student_id = ? ORDER BY date DESC",
        (student_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        payments=payments
    )


@app.route('/receive_payment_page/<int:student_id>')
def receive_payment_page(student_id):
    check = login_required()

    if check:

        return check

    conn = connect_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id=?",
        (student_id,)
    ).fetchone()

    conn.close()

    return render_template(
        "receive_payment.html",
        student=student
    )

@app.route("/pending_payments")
def pending_payments():
    check = login_required()

    if check:

        return check

    conn = connect_db()
    admin_id = session['admin_id']

    students = conn.execute(

        """

        SELECT *

        FROM students

        WHERE admin_id = ?

        AND remaining_amount > 0

        ORDER BY remaining_amount DESC

        """,

        (admin_id,)

    ).fetchall()

    conn.close()

    return render_template(
        "pending_payments.html",
        students=students
    )


@app.route('/download_pending_pdf')
def download_pending_pdf():
    check = login_required()

    if check:

        return check

    conn = connect_db()
    admin_id = session['admin_id']

    students = conn.execute(

        """

        SELECT name, hostel, remaining_amount

        FROM students

        WHERE admin_id = ?

        AND remaining_amount > 0

        ORDER BY remaining_amount DESC

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
def download_students_pdf():
    check = login_required()

    if check:

        return check

    conn = connect_db()
    admin_id = session['admin_id']

    students = conn.execute(

        """

        SELECT name,

            hostel,

            room,

            remaining_amount

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