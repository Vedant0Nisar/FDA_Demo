import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import Json
from datetime import datetime

# Default to user's config
DEFAULT_DB_URL = "postgresql://postgres:1234@localhost:5432/fda_track"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

def create_database_if_not_exists():
    """
    Connects to the default 'postgres' database to check if 'fda_track' exists.
    If not, creates it.
    """
    try:
        # Parse connection info from DB_URL or just usage hardcoded defaults for the 'postgres' db
        # For simplicity, we assume the same user/pass/host/port as DB_URL but dbname='postgres'
        # A robust way is parsing the string, but here we'll do a simple string replacement for the common case
        if "/fda_track" in DB_URL:
            postgres_url = DB_URL.replace("/fda_track", "/postgres")
        else:
            # Fallback
            postgres_url = "postgresql://postgres:1234@localhost:5432/postgres"

        conn = psycopg2.connect(postgres_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'fda_track'")
        exists = cur.fetchone()
        
        if not exists:
            print("Database 'fda_track' not found. Creating it...")
            cur.execute('CREATE DATABASE fda_track')
            print("Database 'fda_track' created successfully.")
        else:
            print("Database 'fda_track' already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not check/create database: {e}")
        print("Ensure the database 'fda_track' exists or the user has permission to create it.")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please ensure PostgreSQL is running and DATABASE_URL is set.")
        return None

def run_schema(conn):
    print("Initializing Database Schema...")
    cur = conn.cursor()
    try:
        # Resolve path relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, "schema_postgres.sql")
        
        with open(schema_path, "r") as f:
            schema_sql = f.read()
            cur.execute(schema_sql)
        conn.commit()
        print("Schema created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Schema Error: {e}")
    finally:
        cur.close()

def seed_data(conn):
    print("Seeding Sample Data...")
    cur = conn.cursor()
    try:
        # 1. Manufacturers
        manufacturers = [
            ("ABC Pharma", "LIC-ABC-001", "Hyderabad", "contact@abcpharma.com"),
            ("XYZ Lifesciences", "LIC-XYZ-002", "Pune", "info@xyzlife.com"),
            ("SunHealth Pharma", "LIC-SUN-003", "Ahmedabad", "support@sunhealth.com")
        ]
        
        m_map = {} # Name -> ID
        for m in manufacturers:
            cur.execute("""
                INSERT INTO manufacturers (name, license_number, address, contact_email)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (license_number) DO UPDATE SET name=EXCLUDED.name
                RETURNING manufacturer_id, name;
            """, m)
            mid, mname = cur.fetchone()
            m_map[mname] = mid

        # 2. Products
        products = [
            ("ABC Pharma", "Paracetamol 500mg", "Pain relief and fever medicine", "GTIN-PARA-500"),
            ("ABC Pharma", "Paracetamol 500mg", "Pain relief", "GTIN-PARA-TEMP-DUP"), # Handle verify logic later
            ("ABC Pharma", "Ibuprofen 400mg", "Anti-inflammatory tablet", "GTIN-IBU-400"),
            ("XYZ Lifesciences", "Amoxicillin 250mg", "Antibiotic capsule", "GTIN-AMOX-250"),
            ("XYZ Lifesciences", "Cough Syrup", "Relief from dry cough", "GTIN-COUGH-SYR"),
            ("SunHealth Pharma", "Vitamin C Tablets", "Immunity booster tablets", "GTIN-VITC-100")
        ]
        
        p_map = {} # (MfgID, Name) -> ProdID
        for m_name, p_name, desc, gtin in products:
            if m_name in m_map:
                cur.execute("""
                    INSERT INTO products (manufacturer_id, name, description, gtin)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (gtin) DO NOTHING
                    RETURNING product_id;
                """, (m_map[m_name], p_name, desc, gtin))
                res = cur.fetchone()
                if res:
                    p_map[(m_map[m_name], p_name)] = res[0]
                else: 
                     # Fetch existing if skipped
                    cur.execute("SELECT product_id FROM products WHERE gtin = %s", (gtin,))
                    res = cur.fetchone()
                    if res:
                        p_map[(m_map[m_name], p_name)] = res[0]

        # 3. Batches (Using User Data)
        batches = [
            ("BATCH-001", "ABC Pharma", "Paracetamol 500mg", "2025-01-01", "2027-01-01", 10000),
            ("BATCH-002", "ABC Pharma", "Ibuprofen 400mg", "2025-01-05", "2027-01-05", 8000),
            ("BATCH-003", "XYZ Lifesciences", "Amoxicillin 250mg", "2025-02-01", "2027-02-01", 12000),
            ("BATCH-004", "XYZ Lifesciences", "Cough Syrup", "2025-02-10", "2026-08-10", 6000),
            ("BATCH-005", "SunHealth Pharma", "Vitamin C Tablets", "2025-03-01", "2027-03-01", 15000),
        ]

        for b_id, m_name, p_name, mfg, exp, size in batches:
            m_id = m_map.get(m_name)
            p_id = p_map.get((m_id, p_name))
            
            if m_id and p_id:
                cur.execute("""
                    INSERT INTO batches (batch_id, product_id, manufacturer_id, mfg_date, exp_date, batch_size, current_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'RELEASED')
                    ON CONFLICT (batch_id) DO NOTHING;
                """, (b_id, p_id, m_id, mfg, exp, size))

        # 4. Shipments
        shipments = [
            ("DS-2023-001", "Warehouse_A_Dock_12", "Distribution_Center_North", "BLK-CHAIN-8823-X9"),
            ("DS-2023-002", "Factory_Zone_B", "Port_Authority_Gate_4", "BLK-CHAIN-9941-Y2"),
            ("DS-2023-003", "Supplier_Depot_West", "Unknown", "BLK-CHAIN-1102-Z5")
        ]

        for s_id, src, dst, blk_hash in shipments:
            cur.execute("""
                INSERT INTO shipments (shipment_id, source_location, destination_location, blockchain_hash, status)
                VALUES (%s, %s, %s, %s, 'SHIPPED')
                ON CONFLICT (shipment_id) DO NOTHING;
            """, (s_id, src, dst, blk_hash))

        # 5. Retailers
        retailers = [
            ("RET-MH-NGP-001", "Jeevan Medico", "Nagpur", 21.1458, 79.0882),
            ("RET-MH-PUN-002", "Apollo Pharmacy", "Pune", 18.5204, 73.8567),
            ("RET-MH-MUM-003", "City Hospital Pharmacy", "Thane", 19.2183, 72.9781),
        ]

        for r_id, name, city, lat, lng in retailers:
            cur.execute("""
                INSERT INTO retailers (retailer_id, name, city, location_lat, location_long)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (retailer_id) DO NOTHING;
            """, (r_id, name, city, lat, lng))

        # 6. Users (Adding Mobile Roles)
        users = [
            ("admin", "System Administrator", "ADMIN", "support@fda.gov"),
            ("inspector_01", "John Inspector", "Inspector", "inspector1@fda.gov"),
            ("auditor_01", "Alice Auditor", "Auditor", "auditor1@fda.gov"),
            ("man_operator", "Manu Operator", "OPERATOR", "operator@abcpharma.com")
        ]

        for uname, fname, role, email in users:
            cur.execute("""
                INSERT INTO users (username, full_name, role, email)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING;
            """, (uname, fname, role, email))

        conn.commit()
        print("Sample data seeded successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Seeding Error: {e}")
    finally:
        cur.close()

if __name__ == "__main__":
    create_database_if_not_exists()
    conn = get_db_connection()
    if conn:
        run_schema(conn)
        seed_data(conn)
        conn.close()
