import psycopg2
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/fda_track")

def fix_and_seed_users():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Reset serial 
    cur.execute("SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users))")
    
    users = [
        ("inspector_01", "John Inspector", "Inspector", "inspector1@fda.gov"),
        ("auditor_01", "Alice Auditor", "Auditor", "auditor1@fda.gov"),
    ]

    for uname, fname, role, email in users:
        cur.execute("""
            INSERT INTO users (username, full_name, role, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
        """, (uname, fname, role, email))
        
    conn.commit()
    print("Mobile users seeded successfully.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_and_seed_users()
