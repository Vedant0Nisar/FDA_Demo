import json
from datetime import datetime
from psycopg2.extras import RealDictCursor, Json

class COAService:
    @staticmethod
    def create_coa(batch_id: str, data: dict, db: RealDictCursor):
        """
        Creates a new COA entry for a batch.
        """
        # Save signature to file (or just keep base64 for now if small enough, 
        # but Plan said save path. For simplicity in demo, let's store base64 or a mock path)
        # We'll use the base64 string directly in the template for now to avoid filesystem complexity issues in demo environment.
        
        db.execute("""
            INSERT INTO coa_certificates (batch_id, analysis_results, signature_path, conclusion)
            VALUES (%s, %s, %s, %s)
            RETURNING coa_id
        """, (batch_id, Json(data['analysis_results']), data['signature_base64'], data['conclusion']))
        
        return db.fetchone()

    @staticmethod
    def get_coa(batch_id: str, db: RealDictCursor):
        db.execute("""
            SELECT c.*, b.product_id, b.mfg_date, b.exp_date, b.batch_size, 
                   m.name as manufacturer_name, m.license_number, m.address,
                   p.name as product_name
            FROM coa_certificates c
            JOIN batches b ON c.batch_id = b.batch_id
            JOIN manufacturers m ON b.manufacturer_id = m.manufacturer_id
            JOIN products p ON b.product_id = p.product_id
            WHERE c.batch_id = %s
        """, (batch_id,))
        return db.fetchone()

    @staticmethod
    def update_approval_status(batch_id: str, status: str, db: RealDictCursor):
        db.execute("UPDATE batches SET fda_approval_status = %s WHERE batch_id = %s", (status, batch_id))
        
        # If approved, also release the batch logic?
        if status == 'APPROVED':
            db.execute("UPDATE batches SET current_status = 'RELEASED' WHERE batch_id = %s", (batch_id,))
            db.execute("UPDATE coa_certificates SET is_released = TRUE WHERE batch_id = %s", (batch_id,))
            
        return status
