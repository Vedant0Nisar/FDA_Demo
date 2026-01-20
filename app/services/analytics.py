from app.database import get_db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    
    @staticmethod
    def build_supply_chain_tree(batch_id: str, db):
        """
        Reconstructs the supply chain tree for a given batch.
        Calculates stock at each node and validates integrity.
        """
        
        # 1. Fetch Batch Info (Root)
        db.execute("""
            SELECT b.*, m.name as manufacturer_name 
            FROM batches b
            JOIN manufacturers m ON b.manufacturer_id = m.manufacturer_id
            WHERE b.batch_id = %s
        """, (batch_id,))
        batch = db.fetchone()
        
        if not batch:
            return None

        # 2. Fetch All Events
        db.execute("""
            SELECT * FROM batch_events 
            WHERE batch_id = %s 
            ORDER BY timestamp ASC
        """, (batch_id,))
        events = db.fetchall()

        # 3. Initialize Tree Structure
        root_node = {
            "id": "MANUFACTURER",
            "name": batch['manufacturer_name'],
            "role": "Manufacturer",
            "received_qty": batch['batch_size'],
            "current_stock": batch['batch_size'],
            "children": [],
            "alerts": []
        }
        
        # Map to track nodes by a unique key (Role + ID/Name) to handle splits
        # For this demo, we assume:
        # Manufacturer -> C&F -> Distributors -> Retailers
        nodes_map = {
            "MANUFACTURER": root_node
        }

        # 4. Process Events to Build Tree
        # specific logic for the demo's event types
        cnf_node_key = None
        
                
        for e in events:
            action = e['action_type']
            qty = e.get('quantity') or 0
            meta = e.get('metadata') or {}
            
            if action == "PRODUCED":
                continue 

            elif action == "RECEIVED_AT_CNF":
                op_name = meta.get('operator_name') or "C&F Agent"
                key = f"CNF_{op_name}"
                
                if key not in nodes_map:
                    node = {
                        "id": key,
                        "name": op_name,
                        "role": "C&F Agent",
                        "received_qty": 0,
                        "current_stock": 0,
                        "children": [], 
                        "alerts": []
                    }
                    nodes_map[key] = node
                    nodes_map["MANUFACTURER"]["children"].append(node)
                    nodes_map["MANUFACTURER"]["current_stock"] -= qty
                    cnf_node_key = key 
                
                nodes_map[key]["received_qty"] += qty
                nodes_map[key]["current_stock"] += qty

            elif action == "RECEIVED_AT_DISTRIBUTOR":
                op_name = meta.get('operator_name') or "Distributor"
                key = f"DIST_{op_name}"
                
                if key not in nodes_map:
                    node = {
                        "id": key,
                        "name": op_name,
                        "role": "Distributor",
                        "received_qty": 0,
                        "current_stock": 0,
                        "children": [],
                        "alerts": [],
                        "location": meta.get('location')
                    }
                    nodes_map[key] = node
                    
                    # Link to active C&F
                    parent_key = cnf_node_key if cnf_node_key else "MANUFACTURER"
                    # Deduct from parent only if not already deducted (logic check needed)
                    # For demo: assume qty here was moved FROM parent
                    if nodes_map[parent_key]["current_stock"] >= qty:
                        nodes_map[parent_key]["children"].append(node)
                        nodes_map[parent_key]["current_stock"] -= qty
                    else:
                        # Logic hole: if stock mismatch, still show link but alert
                        nodes_map[parent_key]["children"].append(node)
                        nodes_map[parent_key]["current_stock"] -= qty # Will go negative, caught by validation
                
                nodes_map[key]["received_qty"] += qty
                nodes_map[key]["current_stock"] += qty

            elif action == "RECEIVED_AT_STORE":
                op_name = meta.get('operator_name') or "Pharmacy"
                key = f"PHARM_{op_name}"
                
                if key not in nodes_map:
                    node = {
                        "id": key,
                        "name": op_name,
                        "role": "Pharmacist",
                        "received_qty": 0,
                        "current_stock": 0,
                        "children": [],
                        "alerts": [],
                        "location": meta.get('location')
                    }
                    nodes_map[key] = node
                    
                    # Find distributor with stock
                    parent_key = None
                    # Prioritize finding a distributor that has enough stock
                    for k, v in nodes_map.items():
                        if v['role'] == 'Distributor' and v['current_stock'] >= qty:
                            parent_key = k
                            break
                    
                    # If no distributor has enough, jsut grab any distributor (simulating error/split?)
                    if not parent_key:
                        for k, v in nodes_map.items():
                            if v['role'] == 'Distributor':
                                parent_key = k
                                break

                    if not parent_key: 
                        parent_key = "MANUFACTURER" 
                        node["alerts"].append("Source unknown")

                    nodes_map[parent_key]["children"].append(node)
                    nodes_map[parent_key]["current_stock"] -= qty

                nodes_map[key]["received_qty"] += qty
                nodes_map[key]["current_stock"] += qty

            elif action == "SOLD_TO_CONSUMER":
                op_name = meta.get('operator_name') or "Pharmacy"
                key = f"PHARM_{op_name}"
                
                # If we can't find the pharmacy by name, try finding any pharmacy with stock
                if key not in nodes_map:
                     for k, v in nodes_map.items():
                        if v['role'] == 'Pharmacist' and v['current_stock'] >= qty:
                            key = k
                            break
                
                if key in nodes_map:
                    nodes_map[key]["current_stock"] -= qty
                    nodes_map[key]["children"].append({
                        "id": f"CONSUMER_{e['event_id']}",
                        "name": "End User",
                        "role": "Consumer",
                        "received_qty": qty,
                        "current_stock": qty,
                        "children": []
                    })
        
        return root_node

    @staticmethod
    def check_conservation_of_mass(node):
        """
        Recursively checks if Outflow > Inflow
        """
        errors = []
        
        # Check Self
        if node['current_stock'] < 0:
            errors.append(f"Node {node['name']} has negative stock: {node['current_stock']}")
            node['alerts'].append("Negative Stock Detected")

        # Check Children Sum vs Self Distributed
        # (Implicitly handled by decrementing current_stock during build, but good to sanity check)
        
        for child in node['children']:
             child_errors = AnalyticsService.check_conservation_of_mass(child)
             errors.extend(child_errors)
             
        return errors
