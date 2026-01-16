import os
import psycopg2
from psycopg2.extras import DictCursor, Json

# Shared DB URL
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/fda_track")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def run_verification(conn):
    cur = conn.cursor(cursor_factory=DictCursor)
    print("=== FDA Database Verification Running ===\n")

    # 1. Check Batches
    print("[1] Checking Batches Table...")
    cur.execute("SELECT COUNT(*) FROM batches;")
    count = cur.fetchone()[0]
    print(f"    -> Found {count} batches in total.")
    
    cur.execute("SELECT batch_id, current_status FROM batches LIMIT 3;")
    for row in cur.fetchall():
        print(f"    -> Batch: {row['batch_id']} | Status: {row['current_status']}")
    print("")

    # 2. Check Traceability (Join)
    print("[2] Checking Traceability (Batch -> Manufacturer)...")
    cur.execute("""
        SELECT b.batch_id, m.name as manufacturer, p.name as product
        FROM batches b
        JOIN manufacturers m ON b.manufacturer_id = m.manufacturer_id
        JOIN products p ON b.product_id = p.product_id
        WHERE b.batch_id = 'BATCH-001';
    """)
    res = cur.fetchone()
    if res:
        print(f"    -> Trace Success: {res['batch_id']} made by {res['manufacturer']} ({res['product']})")
    else:
        print("    -> Trace Failed!")
    print("")

    # 3. Test Anti-Counterfeit Logic (Stored Function)
    print("[3] Testing Anti-Counterfeit Verification Logic...")
    
    # Test A: valid
    batch_id = 'BATCH-001'
    cur.callproc('verify_product', [batch_id])
    row = cur.fetchone() # returns (status, message, name, exp)
    print(f"    -> Scanning '{batch_id}': Status={row[0]}")
    print(f"       Message: {row[1]}")

    # Test B: Invalid
    fake_id = 'BATCH-FAKE-999'
    cur.callproc('verify_product', [fake_id])
    row = cur.fetchone()
    print(f"    -> Scanning '{fake_id}': Status={row[0]}")
    print(f"       Message: {row[1]}")

    print("\n=== Verification Complete ===")
    cur.close()

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        run_verification(conn)
        conn.close()
