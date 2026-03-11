from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import io
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey123"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_conn():
    conn = sqlite3.connect("vendor.db")
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# CREATE TABLES
# -----------------------------
def create_tables():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        mobile TEXT,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendor_details(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_name TEXT,
        item TEXT,
        specifications TEXT,
        price REAL,
        gst_percent REAL,
        additional_charges REAL,
        contact TEXT,
        category TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# SAFE NUMBER CONVERSIONS
# -----------------------------
def to_float(val):
    try:
        return float(val)
    except:
        return 0.0


def to_int(val):
    try:
        return int(val)
    except:
        return 0


# -----------------------------
# TOTAL PRICE
# -----------------------------
def calculate_total(v):

    price = to_float(v["price"])
    gst_percent = to_float(v["gst_percent"])
    charges = to_float(v["additional_charges"])

    gst = price * gst_percent / 100

    return price + gst + charges


# -----------------------------
# AI SCORE
# -----------------------------
def vendor_score(v):

    total = to_float(v["price"])
    rating = 4
    delivery_days = 3

    price_score = 100000 / total if total > 0 else 0
    delivery_score = 50 / delivery_days
    rating_score = rating * 20

    score = price_score + rating_score + delivery_score

    return round(score, 2)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# SIGNUP
# -----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (name,email,mobile,password) VALUES (?,?,?,?)",
            (name, email, mobile, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = email
            return redirect("/vendors")

        else:
            return "Invalid email or password"

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# -----------------------------
# VENDORS LIST
# -----------------------------
@app.route("/vendors")
def vendors():

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vendor_details")
    rows = cur.fetchall()

    conn.close()

    vendors_list = []

    for r in rows:

        vendor = dict(r)

        vendor["total"] = calculate_total(vendor)
        vendor["score"] = vendor_score(vendor)

        vendors_list.append(vendor)

    vendors_list = sorted(vendors_list, key=lambda x: x["score"], reverse=True)

    for i, v in enumerate(vendors_list):
        v["rank"] = i + 1

    best = vendors_list[0] if vendors_list else None

    return render_template("vendors.html", vendors=vendors_list, best=best)


# -----------------------------
# VENDOR DETAIL
# -----------------------------
@app.route("/vendor/<int:vendor_id>")
def vendor_detail(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vendor_details WHERE id=?", (vendor_id,))
    r = cur.fetchone()

    conn.close()

    if not r:
        return "Vendor not found"

    vendor = dict(r)

    vendor["total"] = calculate_total(vendor)
    vendor["score"] = vendor_score(vendor)

    return render_template("vendor_detail.html", vendor=vendor)


# -----------------------------
# ADD VENDOR
# -----------------------------
@app.route("/add_vendor", methods=["GET", "POST"])
def add_vendor():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        vendor_name = request.form['vendor_name']
        item = request.form['item']
        specifications = request.form['specifications']
        price = to_float(request.form['price'])
        gst_percent = to_float(request.form['gst_percent'])
        additional_charges = to_float(request.form['additional_charges'])
        contact = request.form['contact']
        category = request.form['category']

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO vendor_details
        (vendor_name,item,specifications,price,gst_percent,additional_charges,contact,category)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (vendor_name,item,specifications,price,gst_percent,additional_charges,contact,category))

        conn.commit()
        conn.close()

        return redirect("/vendors")

    return render_template("add_vendor.html")


# -----------------------------
# EDIT VENDOR
# -----------------------------
@app.route("/edit_vendor/<int:vendor_id>", methods=["GET","POST"])
def edit_vendor(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":

        vendor_name = request.form['vendor_name']
        item = request.form['item']
        specifications = request.form['specifications']
        price = to_float(request.form['price'])
        gst_percent = to_float(request.form['gst_percent'])
        additional_charges = to_float(request.form['additional_charges'])
        contact = request.form['contact']
        category = request.form['category']

        cur.execute("""
        UPDATE vendor_details
        SET vendor_name=?,item=?,specifications=?,
        price=?,gst_percent=?,additional_charges=?,
        contact=?,category=?
        WHERE id=?
        """,
        (vendor_name,item,specifications,price,gst_percent,
         additional_charges,contact,category,vendor_id))

        conn.commit()
        conn.close()

        return redirect("/vendors")

    cur.execute("SELECT * FROM vendor_details WHERE id=?", (vendor_id,))
    vendor = cur.fetchone()

    conn.close()

    return render_template("edit_vendor.html",vendor=vendor)


# -----------------------------
# DELETE VENDOR
# -----------------------------
@app.route("/delete_vendor/<int:vendor_id>")
def delete_vendor(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM vendor_details WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()

    return redirect("/vendors")


# -----------------------------
# PDF DOWNLOAD
# -----------------------------
@app.route("/download/<int:vendor_id>")
def download(vendor_id):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vendor_details WHERE id=?", (vendor_id,))
    r = cur.fetchone()

    conn.close()

    if not r:
        return "Vendor not found"

    vendor = dict(r)
    total = calculate_total(vendor)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    p.drawString(200,780,"Vendor Purchase Report")

    p.drawString(100,740,f"Vendor: {vendor['vendor_name']}")
    p.drawString(100,720,f"Item: {vendor['item']}")
    p.drawString(100,700,f"Specifications: {vendor['specifications']}")
    p.drawString(100,680,f"Category: {vendor['category']}")
    p.drawString(100,660,f"Price: {vendor['price']}")
    p.drawString(100,640,f"GST: {vendor['gst_percent']}%")
    p.drawString(100,620,f"Charges: {vendor['additional_charges']}")
    p.drawString(100,600,f"Total: {total}")
    p.drawString(100,580,f"Contact: {vendor['contact']}")

    p.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vendor_report.pdf",
        mimetype="application/pdf"
    )


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
