// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MedicineRegistry {
    struct Medicine {
        string batchId;
        string name;
        address manufacturer;
        bool isRegistered;
        string[] details; // [factory_id, batch, shift, operator, mfg, exp, desc, disp, disp_id, temp, loc]
    }

    struct History {
        string incoming;
        string outgoing;
        string exitTime;
        address officer;
    }

    mapping(string => Medicine) public medicines;
    mapping(string => History[]) public historyLog;

    event Registered(string batchId, string name, address manufacturer);
    event Moved(string batchId, string incoming, string outgoing, string exitTime);

    function registerMedicine(string memory _batchId, string memory _name, string[] memory _details) public {
        require(!medicines[_batchId].isRegistered, "Batch already registered");
        
        medicines[_batchId] = Medicine({
            batchId: _batchId,
            name: _name,
            manufacturer: msg.sender,
            isRegistered: true,
            details: _details
        });

        emit Registered(_batchId, _name, msg.sender);
    }

    function updateLogistics(string memory _batchId, string memory _in, string memory _out, string memory _time) public {
        require(medicines[_batchId].isRegistered, "Batch not found");
        
        History memory log = History({
            incoming: _in,
            outgoing: _out,
            exitTime: _time,
            officer: msg.sender
        });

        historyLog[_batchId].push(log);
        emit Moved(_batchId, _in, _out, _time);
    }

    function getHistory(string memory _batchId) public view returns (History[] memory) {
        return historyLog[_batchId];
    }
}
