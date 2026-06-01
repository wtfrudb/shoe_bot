import sqlite3

def check_db():
    conn = sqlite3.connect('shoe_shop.db')
    cursor = conn.cursor()

    print("--- ТОВАРЫ ---")
    cursor.execute("SELECT * FROM shoes")
    for row in cursor.fetchall():
        print(row)

    print("\n--- ВАРИАНТЫ (ЦВЕТА) ---")
    cursor.execute("SELECT * FROM shoe_variants")
    for row in cursor.fetchall():
        print(row)

    print("\n--- НАЛИЧИЕ (РАЗМЕРЫ) ---")
    cursor.execute("SELECT * FROM stock")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == '__main__':
    check_db()