from flask import Flask, render_template, request, redirect, session, send_file
import psycopg2
import psycopg2.extras
import io
import os
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# -----------------------------
# DATABASE CONFIG (Render friendly)
# -----------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)


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
# TOTAL PRICE CALCULATION
# -----------------------------

def calculate_total(v):

    price = to_float(v.get("price"))
    gst_percent = to_float(v.get("gst_percent"))
    charges = to_float(v.get("additional_charges"))

    gst = price * gst_percent / 100

    return price + gst + charges


# -----------------------------
# AI VENDOR SCORE
# -----------------------------

def vendor_score(v):

    total = to_float(v.get("total"))
    rating = to_float(v.get("rating", 4))
    delivery_days = to_int(v.get("delivery_days", 3))

    if total <= 0:
        price_score = 0
    else:
        price_score = 100000 / total

    if delivery_days <= 0:
        delivery_score = 0
    else:
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
            "INSERT INTO users (name,email,mobile,password) VALUES (%s,%s,%s,%s)",
            (name, email, mobile, password)
        )

        conn.commit()
        cur.close()
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
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"] = user["email"]
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM vendor_details")
    rows = cur.fetchall()

    cur.close()
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM vendor_details WHERE id=%s", (vendor_id,))
    r = cur.fetchone()

    cur.close()
    conn.close()

    if not r:
        return "Vendor not found"

    vendor = dict(r)

    vendor["total"] = calculate_total(vendor)
    vendor["score"] = vendor_score(vendor)

    return render_template("vendor_detail.html", vendor=vendor)


# -----------------------------
# DELETE VENDOR
# -----------------------------

@app.route("/delete_vendor/<int:vendor_id>")
def delete_vendor(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM vendor_details WHERE id=%s",(vendor_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/vendors")


# -----------------------------
# PDF DOWNLOAD
# -----------------------------

@app.route("/download/<int:vendor_id>")
def download(vendor_id):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM vendor_details WHERE id=%s",(vendor_id,))
    r = cur.fetchone()

    cur.close()
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


if __name__ == "__main__":
    app.run(debug=True)
