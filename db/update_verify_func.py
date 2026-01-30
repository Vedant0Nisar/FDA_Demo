import os
import psycopg2

DEFAULT_DB_URL = "postgresql://postgres:1234@localhost:5432/fda_track"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

def update_function():
    print("Updating verify_product function...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            CREATE OR REPLACE FUNCTION verify_product(p_batch_id VARCHAR)
            RETURNS TABLE(status VARCHAR, message TEXT, product_name VARCHAR, exp_date DATE) AS $$
            DECLARE
                v_batch RECORD;
            BEGIN
                SELECT b.batch_id, b.current_status, b.exp_date, p.name AS product_name
                INTO v_batch
                FROM batches b
                JOIN products p ON b.product_id = p.product_id
                WHERE b.batch_id = p_batch_id;
            
                IF NOT FOUND THEN
                    status := 'COUNTERFEIT';
                    message := 'ALERT: Product Batch ID not found in official registry. Potential Counterfeit.';
                    product_name := NULL;
                    exp_date := NULL;
                ELSIF v_batch.current_status = 'RECALLED' THEN
                    status := 'WARNING';
                    message := 'DANGER: This batch has been RECALLED. Do not consume.';
                    product_name := v_batch.product_name;
                    exp_date := v_batch.exp_date;
                ELSIF v_batch.current_status = 'QUARANTINE' THEN
                    status := 'WARNING';
                    message := 'NOTICE: Batch is under Quality Quarantine. Not released for sale.';
                    product_name := v_batch.product_name;
                    exp_date := v_batch.exp_date;
                ELSIF v_batch.exp_date < CURRENT_DATE THEN
                    status := 'WARNING';
                    message := 'Product has EXPIRED.';
                    product_name := v_batch.product_name;
                    exp_date := v_batch.exp_date;
                ELSE
                    status := 'AUTHENTIC';
                    message := 'Success: Product is genuine and verified.';
                    product_name := v_batch.product_name;
                    exp_date := v_batch.exp_date;
                END IF;
            
                -- Log the verification attempt
                INSERT INTO verification_logs (scanned_batch_id, verification_result, notes)
                VALUES (p_batch_id, status, message);
            
                RETURN NEXT;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        print("Function updated successfully.")
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Update Error: {e}")

if __name__ == "__main__":
    update_function()
