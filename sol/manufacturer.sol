// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicineSupplyChain {
    
    struct Medicine {
        string batch_id;
        string medicine_name;
        string[] details; // Stores: f_id, f_batch, f_shift, op_id, exp, mfg, desc, d_date, d_id, d_tall
        address manufacturer;
    }

    mapping(string => Medicine) public medicines;

    function registerMedicine(
        string memory _bId, 
        string memory _name, 
        string[] memory _otherDetails
    ) public {
        require(bytes(medicines[_bId].batch_id).length == 0, "Batch ID already exists!");

        medicines[_bId].batch_id = _bId;
        medicines[_bId].medicine_name = _name;
        medicines[_bId].details = _otherDetails;
        medicines[_bId].manufacturer = msg.sender;
    }

    // Helper function to get the details back for the demo
    function getMedicineDetails(string memory _bId) public view returns (string[] memory) {
        return medicines[_bId].details;
    }
}