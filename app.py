from flask import Flask, render_template, request, redirect, flash
import sqlite3
import csv
from flask import Response

app = Flask(__name__)
app.secret_key = "mess_manager_secret"

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

    # payments table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


create_tables()




@app.route('/')
def home():
    return render_template("home.html")




@app.route('/add_student_page')
def add_student_page():
    return render_template("add_student.html")




@app.route('/student_list')
def student_list():

    hostel = request.args.get('hostel')

    conn = connect_db()

    if hostel:
        students = conn.execute(
            "SELECT * FROM students WHERE hostel = ?",
            (hostel,)
        ).fetchall()
    else:
        students = conn.execute(
            "SELECT * FROM students"
        ).fetchall()

    conn.close()

    return render_template("student_list.html", students=students)




@app.route('/payment_page')
def payment_page():

    conn = connect_db()

    students = conn.execute(
        "SELECT id, name, remaining_amount FROM students"
    ).fetchall()

    conn.close()

    return render_template("payment.html", students=students)




@app.route('/add_student', methods=['POST'])
def add_student():

    name = request.form['name']
    room = request.form['room']
    hostel = request.form['hostel']

    conn = connect_db()

    conn.execute(
        "INSERT INTO students (name, room, hostel) VALUES (?, ?, ?)",
        (name, room, hostel)
    )

    conn.commit()
    conn.close()

    flash("Student added successfully!")
    return redirect('/add_student_page')




@app.route('/payment_history/<int:student_id>')
def payment_history(student_id):

    conn = connect_db()

    history = conn.execute(
        "SELECT amount, date FROM payments WHERE student_id = ? ORDER BY date DESC",
        (student_id,)
    ).fetchall()

    conn.close()

    return render_template("payment_history.html", history=history)




@app.route('/receive_payment', methods=['POST'])
def receive_payment():

    student_id = request.form['student_id']
    amount = int(request.form['amount'])

    conn = connect_db()

    # get current values
    student = conn.execute(
        "SELECT received_amount, remaining_amount FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    received = student[0] + amount
    remaining = student[1] - amount

    # update database
    conn.execute(
        "UPDATE students SET received_amount = ?, remaining_amount = ? WHERE id = ?",
        (received, remaining, student_id)
    )

    conn.execute(
        "INSERT INTO payments (student_id, amount) VALUES (?, ?)",
        (student_id, amount)
)

    conn.commit()
    conn.close()

    flash("Payment received successfully!")
    return redirect('/payment_page')



@app.route('/test')
def test():
    return "Test route working"



@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):

    conn = connect_db()

    conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    conn.commit()
    conn.close()

    flash("Student deleted successfully!")

    return redirect('/student_list')



@app.route('/edit_student/<int:student_id>')
def edit_student(student_id):

    conn = connect_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    conn.close()

    return render_template("edit_student.html", student=student)




@app.route('/update_student', methods=['POST'])
def update_student():

    student_id = request.form['id']
    name = request.form['name']
    room = request.form['room']
    hostel = request.form['hostel']

    conn = connect_db()

    conn.execute(
        "UPDATE students SET name=?, room=?, hostel=? WHERE id=?",
        (name, room, hostel, student_id)
    )

    conn.commit()
    conn.close()

    flash("Student updated successfully!")

    return redirect('/student_list')





@app.route('/export_csv')
def export_csv():
    conn = connect_db()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    conn.close()

    def generate():
        yield "ID,Name,Room,Hostel,Received,Remaining\n"

        for student in students:
            yield f"{student[0]},{student[1]},{student[2]},{student[3]},{student[4]},{student[5]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_report.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)