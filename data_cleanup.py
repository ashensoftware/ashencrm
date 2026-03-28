import sqlite3

def clean_db():
    conn = sqlite3.connect("data/prospects.db")
    cur = conn.cursor()

    print("[*] Limpiando sitios web 'duckduckgo'...")
    cur.execute("UPDATE prospects SET website = '' WHERE website LIKE '%duckduckgo.com%'")
    print(f" -> Filas web afectadas: {cur.rowcount}")

    print("[*] Limpiando numeros de telefono que son timestamps / basura (ej. 1774045344)...")
    # Borrar si el teléfono empieza por "177" y tiene exactamente 10 digitos (el timestamp de 2026),
    # o si no tiene ningun '+57' o '3' inicial cuando tiene 10 digitos, vamos a borrar los que empiezan por 17.
    # En Colombia, los celulares empiezan con 3 (ej 300 000 0000). Los fijos con +57 o el indicativo.
    # Para estar seguros, limpiaremos todo lo que empiece por '1774' y mida 10:
    cur.execute("UPDATE prospects SET phone = '' WHERE phone LIKE '177%' AND length(phone) = 10")
    print(f" -> Filas telefono afectadas: {cur.rowcount}")

    conn.commit()
    conn.close()
    print("[*] Base de datos reparada correctamente.")

if __name__ == '__main__':
    clean_db()
