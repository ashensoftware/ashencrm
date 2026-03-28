import sqlite3

conn = sqlite3.connect("d:/Ashen/ashencrm/data/prospects.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, name, phone, website, maps_url FROM prospects LIMIT 10")
rows = cur.fetchall()

with open("db_res.txt", "w") as f:
    f.write("MUESTRA DE BASE DE DATOS:\n")
    for r in rows:
        f.write(str(dict(r)) + "\n")

    f.write("\nConteo por domain de website:\n")
    cur.execute("SELECT website, count(*) as c FROM prospects GROUP BY website ORDER BY c DESC LIMIT 10")
    for r in cur.fetchall():
        f.write(str(dict(r)) + "\n")
