from flask import Flask, render_template, request, redirect, send_file, session
import psycopg2
import psycopg2.extras
import io
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "vendor_secret_key"

# -----------------------------
# PostgreSQL connection
# -----------------------------
DB_HOST = "db.xxxxxx.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "anuAnu58"28"


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
        port=DB_PORT,
        sslmode="require"
    )


# -----------------------------
# Calculate total price
# -----------------------------
def calculate_total(v):
    price = float(v['price'])
    gst = price * float(v['gst_percent']) / 100
    charges = float(v['additional_charges'])
    return price + gst + charges


# -----------------------------
# Landing Page
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# Signup
# -----------------------------
@app.route("/signup", methods=["GET","POST"])
def signup():

    if request.method=="POST":

        name=request.form["name"]
        email=request.form["email"]
        mobile=request.form["mobile"]
        password=request.form["password"]

        conn=get_conn()
        cur=conn.cursor()

        cur.execute(
        "INSERT INTO users (name,email,mobile,password) VALUES (%s,%s,%s,%s)",
        (name,email,mobile,password)
        )

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method=="POST":

        email=request.form["email"]
        password=request.form["password"]

        conn=get_conn()
        cur=conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email,password)
        )

        user=cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session["user"]=user["email"]
            return redirect("/vendors")
        else:
            return "Invalid Login"

    return render_template("login.html")


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():
    session.pop("user",None)
    return redirect("/login")


# -----------------------------
# Vendor List Page
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

        vendor = {
            "id": r['id'],
            "vendor_name": r['vendor_name'],
            "item": r['item'],
            "specifications": r['specifications'],
            "price": float(r['price']),
            "gst_percent": float(r['gst_percent']),
            "additional_charges": float(r['additional_charges']),
            "contact": r['contact'],
            "category": r['category']
        }

        vendor["total"] = calculate_total(vendor)

        vendors_list.append(vendor)

    vendors_list = sorted(vendors_list, key=lambda x: x["total"])

    for i, v in enumerate(vendors_list):
        v["rank"] = i + 1

    best = vendors_list[0] if vendors_list else None

    return render_template(
        "vendors.html",
        vendors=vendors_list,
        best=best
    )


# -----------------------------
# Vendor Detail Page
# -----------------------------
@app.route("/vendor/<int:vendor_id>")
def vendor_detail(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT * FROM vendor_details WHERE id = %s",
        (vendor_id,)
    )

    r = cur.fetchone()

    cur.close()
    conn.close()

    if not r:
        return "Vendor not found"

    vendor = {
        "id": r['id'],
        "vendor_name": r['vendor_name'],
        "item": r['item'],
        "specifications": r['specifications'],
        "price": float(r['price']),
        "gst_percent": float(r['gst_percent']),
        "additional_charges": float(r['additional_charges']),
        "contact": r['contact'],
        "category": r['category']
    }

    vendor["total"] = calculate_total(vendor)

    return render_template(
        "vendor_detail.html",
        vendor=vendor
    )


# -----------------------------
# Download PDF Report
# -----------------------------
@app.route("/download/<int:vendor_id>")
def download(vendor_id):

    if "user" not in session:
        return redirect("/login")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT * FROM vendor_details WHERE id = %s",
        (vendor_id,)
    )

    r = cur.fetchone()

    cur.close()
    conn.close()

    if not r:
        return "Vendor not found"

    vendor = {
        "vendor_name": r['vendor_name'],
        "item": r['item'],
        "specifications": r['specifications'],
        "price": float(r['price']),
        "gst_percent": float(r['gst_percent']),
        "additional_charges": float(r['additional_charges'],
        ),
        "contact": r['contact'],
        "category": r['category']
    }

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
# Add Vendor
# -----------------------------
@app.route("/add_vendor", methods=["GET","POST"])
def add_vendor():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        vendor_name = request.form['vendor_name']
        item = request.form['item']
        specifications = request.form['specifications']
        price = float(request.form['price'])
        gst_percent = float(request.form['gst_percent'])
        additional_charges = float(request.form['additional_charges'])
        contact = request.form['contact']
        category = request.form['category']

        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
        """
        INSERT INTO vendor_details
        (vendor_name,item,specifications,price,gst_percent,additional_charges,contact,category)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
        vendor_name,
        item,
        specifications,
        price,
        gst_percent,
        additional_charges,
        contact,
        category
        )
        )

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/vendors")

    return render_template("add_vendor.html")


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
