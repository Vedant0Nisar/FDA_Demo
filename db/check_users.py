import psycopg2
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/fda_track")

def check_users():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users WHERE role IN ('Inspector', 'Auditor')")
    users = cur.fetchall()
    print(f"Found {len(users)} mobile users:")
    for u in users:
        print(f" - {u[0]} ({u[1]})")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_users()
