-- FDA Traceability Database Schema (PostgreSQL)
-- Designed for Anti-Counterfeit, Batch Tracking, and Regulatory Compliance

-- 1. Core Entity Tables (Master Data)

CREATE TABLE IF NOT EXISTS departments (
    department_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- e.g., 'Manufacturing-Floor', 'QA-Lab', 'Logistics-Dispatch'
    location_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(150),
    role VARCHAR(50) NOT NULL, -- 'ADMIN', 'OPERATOR', 'QA_OFFICER', 'DRIVER', 'PHARMACIST'
    department_id INTEGER REFERENCES departments(department_id),
    email VARCHAR(150),
    contact_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manufacturers (
    manufacturer_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    license_number VARCHAR(100) UNIQUE NOT NULL, -- Regulatory License ID
    address TEXT,
    contact_email VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    manufacturer_id INTEGER REFERENCES manufacturers(manufacturer_id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    gtin VARCHAR(50) UNIQUE, -- Global Trade Item Number (Barcode)
    category VARCHAR(50), -- 'Medicine', 'Supplement', 'Vaccine'
    storage_conditions TEXT, -- e.g., 'Keep refrigerated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Operational Tables (Transactions)

CREATE TABLE IF NOT EXISTS batches (
    batch_id VARCHAR(50) PRIMARY KEY, -- Using String ID as per user request (e.g., 'BATCH-001')
    product_id INTEGER REFERENCES products(product_id),
    manufacturer_id INTEGER REFERENCES manufacturers(manufacturer_id),
    mfg_date DATE NOT NULL,
    exp_date DATE NOT NULL,
    batch_size INTEGER,
    current_status VARCHAR(50) DEFAULT 'CREATED', -- 'CREATED', 'IN_QA', 'RELEASED', 'SHIPPED', 'RECALLED'
    fda_approval_status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coa_certificates (
    coa_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) REFERENCES batches(batch_id),
    analysis_results JSONB, -- { "assay": "99.2%", "ph": "6.5" ... }
    signature_path TEXT, -- URL/Path to digital signature image
    conclusion TEXT, -- "Complies with USP standards"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_released BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id VARCHAR(50) PRIMARY KEY, -- e.g., 'DS-2023-001'
    source_location VARCHAR(200),
    destination_location VARCHAR(200),
    vehicle_id VARCHAR(50),
    blockchain_hash VARCHAR(255), -- Hash of the shipment data stored on blockchain
    status VARCHAR(50) DEFAULT 'IN_TRANSIT',
    departure_time TIMESTAMP,
    arrival_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS retailers (
    retailer_id VARCHAR(50) PRIMARY KEY, -- e.g., 'RET-MH-NGP-001'
    name VARCHAR(200),
    license_number VARCHAR(100),
    location_lat DECIMAL(9,6),
    location_long DECIMAL(9,6),
    address TEXT,
    city VARCHAR(100),
    contact_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Traceability & Audit Tables

CREATE TABLE IF NOT EXISTS batch_events (
    event_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) REFERENCES batches(batch_id),
    user_id INTEGER REFERENCES users(user_id),
    department_id INTEGER REFERENCES departments(department_id),
    action_type VARCHAR(50) NOT NULL, -- 'PRODUCED', 'QUALITY_CHECK', 'PACKED', 'SHIPPED', 'RECEIVED_AT_RETAIL'
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB, -- Flexible field for sensor data, digital signatures, GPS, etc.
    blockchain_tx_id VARCHAR(255) -- Optional link to specific blockchain transaction
);

-- Junction table for Batches in a Shipment
CREATE TABLE IF NOT EXISTS shipment_items (
    shipment_id VARCHAR(50) REFERENCES shipments(shipment_id),
    batch_id VARCHAR(50) REFERENCES batches(batch_id),
    quantity INTEGER,
    PRIMARY KEY (shipment_id, batch_id)
);

-- 4. Anti-Counterfeit Verification

CREATE TABLE IF NOT EXISTS verification_logs (
    log_id SERIAL PRIMARY KEY,
    scanned_batch_id VARCHAR(50), -- Input ID (may not exist in batches table if fake)
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    geo_location JSONB, -- { "lat": ..., "long": ... }
    scanned_by_user_agent TEXT, -- Browser/App info
    verification_result VARCHAR(50), -- 'AUTHENTIC', 'COUNTERFEIT', 'RECALLED', 'EXPIRED'
    notes TEXT
);

-- 5. Alert System (Fraud/Reporting)
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) REFERENCES batches(batch_id),
    node_id VARCHAR(100), -- The node/location where the alert was triggered
    status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'INVESTIGATING', 'RESOLVED'
    severity VARCHAR(20) DEFAULT 'HIGH',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Stored Functions for Logic

-- Function to verify a product scan
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
