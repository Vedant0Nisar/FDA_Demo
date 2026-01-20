import json
import logging
from web3 import Web3
from app.blockchain_config import RPC_URL, ADDR_TRACKER, ABI_TRACKER, ADDR_DISTRIBUTOR, ABI_DISTRIBUTOR, ADDR_RETAILER, ABI_RETAILER

logger = logging.getLogger(__name__)

class BlockchainService:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Contracts
    start_account = w3.eth.accounts[0] # Default
    
    contract_tracker = w3.eth.contract(address=ADDR_TRACKER, abi=ABI_TRACKER)
    contract_distributor = w3.eth.contract(address=ADDR_DISTRIBUTOR, abi=ABI_DISTRIBUTOR)
    contract_retailer = w3.eth.contract(address=ADDR_RETAILER, abi=ABI_RETAILER)

    @classmethod
    def register_product(cls, batch_id: str, name: str, details: list) -> str:
        """ Registers in C&F.sol (MedicineTracker) """
        try:
            tx_hash = cls.contract_tracker.functions.registerMedicine(
                batch_id, name, details or []
            ).transact({'from': cls.start_account})
            cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Reg Error: {e}")
            raise e

    @classmethod
    def log_movement(cls, batch_id: str, incoming: str, outgoing: str, timestamp: str, quantity: int) -> str:
        """ Logs movement in C&F.sol """
        try:
            tx_hash = cls.contract_tracker.functions.updateLogistics(
                batch_id, incoming, outgoing, timestamp, quantity
            ).transact({'from': cls.start_account})
            cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Mov Filter Error: {e}")
            raise e

    @classmethod
    def log_distributor(cls, batch_id: str, dist_id: str, cap: str, stock: str, ingress: str, egress: str, eye: str, quantity: int) -> str:
        """ Logs to distributor.sol """
        try:
            tx_hash = cls.contract_distributor.functions.updateDistributor(
                batch_id, dist_id, cap, stock, ingress, egress, eye, quantity
            ).transact({'from': cls.start_account})
            cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Dist Error: {e}")
            raise e

    @classmethod
    def log_retailer(cls, batch_id: str, ret_id: str, r_type: str, shop: str, qty: int, owner: str, contact: str, date: str) -> str:
        """ Logs to retailer.sol """
        try:
            tx_hash = cls.contract_retailer.functions.updateRetailer(
                batch_id, ret_id, r_type, shop, qty, owner, contact, date
            ).transact({'from': cls.start_account})
            cls.w3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Ret Error: {e}")
            raise e

    @classmethod
    def get_batch_details(cls, batch_id: str) -> list:
        """ Fetches immutable details from C&F.sol (Manufacturer Contract) """
        try:
            # Returns list of strings e.g. ["MFG:2025-10-10", "EXP:2026-10-10", ...]
            details = cls.contract_tracker.functions.getMedicineDetails(batch_id).call()
            return details
        except Exception as e:
            logger.error(f"Blockchain Read Error for {batch_id}: {e}")
            # we re-raise because if we can't read the chain, we can't verify (Fail-Closed)
            raise e
