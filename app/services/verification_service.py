
from app.services.blockchain import BlockchainService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VerificationService:
    @staticmethod
    def verify_batch_integrity(batch_id: str, db_cursor) -> dict:
        """
        Performs a Cross-Reference Check between Database and Blockchain.
        Returns a dict with status and message.
        """
        # 1. Fetch from Database
        db_cursor.execute("SELECT mfg_date, exp_date, batch_size, current_status FROM batches WHERE batch_id = %s", (batch_id,))
        db_batch = db_cursor.fetchone()
        
        if not db_batch:
            return {"status": "NOT_FOUND", "message": "Batch ID not found in Database."}

        # --- NEW: Red Flag Protocol ---
        if db_batch['current_status'] == 'UNDER_INVESTIGATION':
            logger.critical(f"SECURITY BLOCK: Batch {batch_id} is UNDER_INVESTIGATION.")
            return {
                "status": "SECURITY_ALERT", 
                "message": "🚨 SECURITY ALERT: This batch has been flagged by FDA Inspectors. Do not accept/sell/consume."
            }
        # ------------------------------

        # 2. Fetch from Blockchain
        try:
            chain_details = BlockchainService.get_batch_details(batch_id)
            # chain_details is a list of strings: ["MFG:2025-01-01", "EXP:...", "SIZE:...", "LIC:..."]
        except Exception as e:
            logger.error(f"Blockchain unreachable: {e}")
            return {"status": "UNKNOWN", "message": "Blockchain verification unavailable. Validation failed-closed."}

        if not chain_details or len(chain_details) == 0:
             # If empty on chain but exists in DB -> Major red flag or simply not synced yet
             return {"status": "WARNING", "message": "Batch found in DB but not on Blockchain."}

        # 3. Parse Chain Data
        chain_data = {}
        for item in chain_details:
            if ":" in item:
                key, val = item.split(":", 1)
                chain_data[key.strip()] = val.strip()

        # 4. Compare
        discrepancies = []
        
        # Compare MFG Date
        # DB returns date object, Chain is string YYYY-MM-DD
        db_mfg = str(db_batch['mfg_date'])
        chain_mfg = chain_data.get('MFG')
        if db_mfg != chain_mfg:
            discrepancies.append(f"MFG Date Mismatch: DB={db_mfg}, Chain={chain_mfg}")

        # Compare EXP Date
        db_exp = str(db_batch['exp_date'])
        chain_exp = chain_data.get('EXP')
        if db_exp != chain_exp:
            discrepancies.append(f"EXP Date Mismatch: DB={db_exp}, Chain={chain_exp}")

        # Compare Size
        db_size = str(db_batch['batch_size'])
        chain_size = chain_data.get('SIZE')
        
        # DEBUG LOGGING
        logger.info(f"VERIFY DEBUG: Batch={batch_id}")
        logger.info(f"DB -> MFG:{db_mfg}, EXP:{db_exp}, SIZE:{db_size}")
        logger.info(f"CHAIN -> MFG:{chain_mfg}, EXP:{chain_exp}, SIZE:{chain_size}")
        logger.info(f"Chain Raw: {chain_details}")

        if db_size != chain_size:
            discrepancies.append(f"Batch Size Mismatch: DB={db_size}, Chain={chain_size}")

        if discrepancies:
            # 5. Log Tamper Alert
            details_str = "; ".join(discrepancies)
            logger.critical(f"TAMPER DETECTED for {batch_id}: {details_str}")
            
            try:
                # A. Log to specific alerts table
                db_cursor.execute("""
                    INSERT INTO tamper_alerts (batch_id, discrepancy_details)
                    VALUES (%s, %s)
                """, (batch_id, details_str))
                
                # B. Log to Audit Trail (batch_events) for Timeline Visibility
                # We use System User (1) for automatic detection
                from psycopg2.extras import Json
                metadata = {"discrepancies": discrepancies, "alert": "Critical Data Mismatch"}
                
                db_cursor.execute("""
                    INSERT INTO batch_events (batch_id, user_id, department_id, action_type, description, metadata, blockchain_tx_id)
                    VALUES (%s, 1, 1, 'TAMPER_ALERT', %s, %s, 'N/A')
                """, (batch_id, f"SECURITY ALERT: {details_str}", Json(metadata)))
                
                # Note: The commit() happens in the route dependency (get_db) upon successful return.
                
            except Exception as e:
                logger.error(f"Failed to log tamper alert: {e}")

            return {
                "status": "TAMPERED", 
                "message": f"Critical Data Mismatch Detected! {details_str}", 
                "details": discrepancies
            }

        return {"status": "AUTHENTIC", "message": "Verified on Blockchain. Data is Integrity Assured."}
