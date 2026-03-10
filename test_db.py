import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="vendor_db",
    user="postgres",
    password="anushka28",
    port="5432"
)

cursor = conn.cursor()

cursor.execute("SELECT * FROM vendor_details")

rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
