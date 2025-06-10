from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import sqlite3
import datetime
import csv
from io import StringIO
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# -----------------------------------------------------------
# Initialize the database and create required tables
# -----------------------------------------------------------
def init_db():
    conn = sqlite3.connect("construction.db")
    cursor = conn.cursor()

    # Projects table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_date TEXT,
        end_date TEXT
    )
    ''')

    # Tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        assigned_to TEXT,
        due_date TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Workers table (human resources)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        name TEXT NOT NULL,
        role TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Materials table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        name TEXT NOT NULL,
        quantity INTEGER,
        unit_cost REAL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Expenses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title TEXT NOT NULL,
        amount REAL,
        description TEXT,
        expense_date TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # Notifications table for task due alerts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        task_id INTEGER,
        message TEXT,
        notified INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Database connection helper with row_factory for dict-like access
def get_db_connection():
    conn = sqlite3.connect("construction.db")
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------------------------------------
# Main routes and CRUD operations
# -----------------------------------------------------------

# Home page: List of projects
@app.route("/")
def index():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("index.html", projects=projects)

# Project details: Including tasks, workers, materials, and expenses
@app.route("/project/<int:project_id>")
def project_detail(project_id):
    conn = get_db_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    tasks = conn.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
    workers = conn.execute("SELECT * FROM workers WHERE project_id = ?", (project_id,)).fetchall()
    materials = conn.execute("SELECT * FROM materials WHERE project_id = ?", (project_id,)).fetchall()
    expenses = conn.execute("SELECT * FROM expenses WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return render_template("project_detail.html", project=project, tasks=tasks,
                           workers=workers, materials=materials, expenses=expenses)

# Add new project
@app.route("/add_project", methods=["GET", "POST"])
def add_project():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO projects (name, description, start_date, end_date) VALUES (?, ?, ?, ?)",
            (name, description, start_date, end_date)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    return render_template("add_project.html")

# Add task to a project
@app.route("/add_task/<int:project_id>", methods=["GET", "POST"])
def add_task(project_id):
    if request.method == "POST":
        name = request.form["name"]
        assigned_to = request.form["assigned_to"]
        due_date = request.form["due_date"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (project_id, name, assigned_to, due_date) VALUES (?, ?, ?, ?)",
            (project_id, name, assigned_to, due_date)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template("add_task.html", project_id=project_id)

# Toggle task status (pending <-> completed)
@app.route("/update_task_status/<int:task_id>")
def update_task_status(task_id):
    conn = get_db_connection()
    task = conn.execute("SELECT project_id, status FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task:
        project_id = task["project_id"]
        current_status = task["status"]
        new_status = "completed" if current_status == "pending" else "pending"
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        conn.commit()
    conn.close()
    return redirect(url_for("project_detail", project_id=project_id))

# Add new worker to a project
@app.route("/add_worker/<int:project_id>", methods=["GET", "POST"])
def add_worker(project_id):
    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO workers (project_id, name, role) VALUES (?, ?, ?)",
            (project_id, name, role)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template("add_worker.html", project_id=project_id)

# Add new material to a project
@app.route("/add_material/<int:project_id>", methods=["GET", "POST"])
def add_material(project_id):
    if request.method == "POST":
        name = request.form["name"]
        quantity = request.form["quantity"]
        unit_cost = request.form["unit_cost"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO materials (project_id, name, quantity, unit_cost) VALUES (?, ?, ?, ?)",
            (project_id, name, quantity, unit_cost)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template("add_material.html", project_id=project_id)

# Add new expense to a project
@app.route("/add_expense/<int:project_id>", methods=["GET", "POST"])
def add_expense(project_id):
    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        description = request.form["description"]
        expense_date = request.form["expense_date"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO expenses (project_id, title, amount, description, expense_date) VALUES (?, ?, ?, ?, ?)",
            (project_id, title, amount, description, expense_date)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template("add_expense.html", project_id=project_id)

# -----------------------------------------------------------
# Reports page: Overall project summary
# -----------------------------------------------------------
@app.route("/reports")
def reports():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    
    report_data = []
    for project in projects:
        project_id = project["id"]
        tasks_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)).fetchone()[0]
        workers_count = conn.execute("SELECT COUNT(*) FROM workers WHERE project_id = ?", (project_id,)).fetchone()[0]
        materials_count = conn.execute("SELECT COUNT(*) FROM materials WHERE project_id = ?", (project_id,)).fetchone()[0]
        total_expense = conn.execute("SELECT SUM(amount) FROM expenses WHERE project_id = ?", (project_id,)).fetchone()[0] or 0
        
        report_data.append({
            "project": project,
            "tasks_count": tasks_count,
            "workers_count": workers_count,
            "materials_count": materials_count,
            "total_expense": total_expense
        })
    conn.close()
    return render_template("reports.html", report_data=report_data)

# -----------------------------------------------------------
# Additional features: Notifications, Charts and Data Interactions
# -----------------------------------------------------------

# Use APScheduler to check for tasks due tomorrow (pending tasks)
def check_due_tasks():
    conn = get_db_connection()
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
    tasks_due = conn.execute(
        "SELECT * FROM tasks WHERE due_date = ? AND status = 'pending'",
        (tomorrow_str,)
    ).fetchall()
    
    for task in tasks_due:
        # If the notification for this task does not exist, create it
        existing = conn.execute("SELECT * FROM notifications WHERE task_id = ?", (task["id"],)).fetchone()
        if not existing:
            message = f"Task '{task['name']}' is due tomorrow."
            conn.execute(
                "INSERT INTO notifications (project_id, task_id, message, created_at) VALUES (?, ?, ?, ?)",
                (task["project_id"], task["id"], message, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
    conn.close()

scheduler = BackgroundScheduler()
# For demo purposes, execute every minute (adjust interval as needed)
scheduler.add_job(func=check_due_tasks, trigger="interval", minutes=1)
scheduler.start()

# Notifications page: Display alerts
@app.route("/notifications")
def notifications():
    conn = get_db_connection()
    notifications = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("notifications.html", notifications=notifications)

# Charts page: Display project expense charts using Chart.js
@app.route("/charts")
def charts():
    conn = get_db_connection()
    projects = conn.execute("SELECT id, name FROM projects").fetchall()
    chart_data = []
    for project in projects:
        total_expense = conn.execute("SELECT SUM(amount) FROM expenses WHERE project_id = ?", (project["id"],)).fetchone()[0] or 0
        chart_data.append({"name": project["name"], "expense": total_expense})
    conn.close()
    return render_template("charts.html", chart_data=chart_data)

# -----------------------------------------------------------------
# Additional Data Interaction Features:
# 1. API: Return projects data in JSON format (suitable for mobile apps etc.)
@app.route("/api/projects")
def api_projects():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    projects_list = [{key: project[key] for key in project.keys()} for project in projects]
    return jsonify(projects_list)

# 2. Data Export: Export projects data as CSV for backups.
@app.route("/export")
def export_data():
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "description", "start_date", "end_date"])
    for project in projects:
        writer.writerow([project["id"], project["name"], project["description"],
                         project["start_date"], project["end_date"]])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=projects.csv"
    return response

# -----------------------------------------------------------
# Instructions for Packaging as a Desktop App:
# -----------------------------------------------------------
# To convert this application into a standalone executable (e.g., for Windows),
# you can use PyInstaller as follows:
#
#   pyinstaller --onefile --add-data "templates;templates" app.py
#
# This command bundles the templates folder into the executable so that Python installation is not required.

if __name__ == "__main__":
    try:
        app.run(debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
