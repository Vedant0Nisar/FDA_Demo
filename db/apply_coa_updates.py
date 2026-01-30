import os
import psycopg2

DEFAULT_DB_URL = "postgresql://postgres:1234@localhost:5432/fda_track"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

def apply_updates():
    print("Applying COA Updates to Database...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Add column to batches if it doesn't exist
        try:
            cur.execute("ALTER TABLE batches ADD COLUMN fda_approval_status VARCHAR(50) DEFAULT 'PENDING';")
            print("Added column 'fda_approval_status' to batches.")
        except Exception as e:
            print(f"Skipping column add (verified existence): {e}")

        # 2. Create COA table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coa_certificates (
                coa_id SERIAL PRIMARY KEY,
                batch_id VARCHAR(50) REFERENCES batches(batch_id),
                analysis_results JSONB,
                signature_path TEXT,
                conclusion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_released BOOLEAN DEFAULT FALSE
            );
        """)
        print("Ensured 'coa_certificates' table exists.")

        conn.commit()
        cur.close()
        conn.close()
        print("Database updates applied successfully.")

    except Exception as e:
        print(f"Migration Error: {e}")

if __name__ == "__main__":
    apply_updates()
