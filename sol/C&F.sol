// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicineTracker {
    struct Medicine {
        string batchId;
        string name;
        string[] details; // [f_id, f_batch, f_shift, op_id, exp, mfg, desc, d_date, d_id, d_tall]
        address manufacturer;
        bool isRegistered;
    }

    struct Movement {
        string incoming;
        string outgoing;
        string exitTime;
        address officer;
    }

    mapping(string => Medicine) public medicines;
    mapping(string => Movement[]) public history;

    event Registered(string batchId, string name, address manufacturer);
    event Moved(string batchId, string incoming, string outgoing, string exitTime);

    function registerMedicine(string memory _batchId, string memory _name, string[] memory _details) public {
        require(!medicines[_batchId].isRegistered, "Batch ID already exists!");
        medicines[_batchId] = Medicine(_batchId, _name, _details, msg.sender, true);
        emit Registered(_batchId, _name, msg.sender);
    }

    function updateLogistics(string memory _batchId, string memory _in, string memory _out, string memory _time) public {
        require(medicines[_batchId].isRegistered, "Medicine not registered!");
        history[_batchId].push(Movement(_in, _out, _time, msg.sender));
        emit Moved(_batchId, _in, _out, _time);
    }
}