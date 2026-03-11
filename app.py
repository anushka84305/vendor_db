from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2 import OperationalError
import os

app = Flask(__name__)
app.secret_key = "vendor_secret"

# -----------------------------
# DATABASE CONFIG
# -----------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "vendor_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "anushka28")
DB_PORT = os.getenv("DB_PORT", "5432")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except OperationalError as e:
        print("Database connection failed:", e)
        return None


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    conn = get_db_connection()

    if conn is None:
        return "Database not connected"

    cur = conn.cursor()

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cur.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cur.fetchone()

        if user:
            session["user"] = username
            return redirect("/vendors")

    return render_template("login.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    conn = get_db_connection()

    if conn is None:
        return "Database not connected"

    cur = conn.cursor()

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cur.execute(
            "INSERT INTO users (username,password) VALUES (%s,%s)",
            (username, password)
        )

        conn.commit()

        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# VENDORS LIST
# -----------------------------
@app.route("/vendors")
def vendors():

    conn = get_db_connection()

    if conn is None:
        return "Database not connected"

    cur = conn.cursor()

    cur.execute("SELECT * FROM vendors")

    vendors = cur.fetchall()

    return render_template("vendors.html", vendors=vendors)


# -----------------------------
# ADD VENDOR
# -----------------------------
@app.route("/add_vendor", methods=["GET", "POST"])
def add_vendor():

    conn = get_db_connection()

    if conn is None:
        return "Database not connected"

    cur = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        quality = request.form["quality"]

        cur.execute(
            "INSERT INTO vendors (name,price,quality) VALUES (%s,%s,%s)",
            (name, price, quality)
        )

        conn.commit()

        return redirect("/vendors")

    return render_template("add_vendors.html")


# -----------------------------
# DELETE VENDOR
# -----------------------------
@app.route("/delete_vendor/<int:id>")
def delete_vendor(id):

    conn = get_db_connection()

    if conn is None:
        return "Database not connected"

    cur = conn.cursor()

    cur.execute("DELETE FROM vendors WHERE id=%s", (id,))

    conn.commit()

    return redirect("/vendors")


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
