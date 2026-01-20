// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DistributorRegistry {
    struct DistributionData {
        string distId;
        string capacity;
        string stock;
        string ingress;
        string egress;
        string doubtEye;
        uint256 quantity; // Added quantity tracking
        bool exists;
    }

    mapping(string => DistributionData[]) public distributions; // Changed to array for splitting
    event DistributorUpdated(string indexed batchId, string distId, string ingress, string egress, uint256 quantity);

    function updateDistributor(
        string memory _batchId,
        string memory _distId,
        string memory _capacity,
        string memory _stock,
        string memory _ingress,
        string memory _egress,
        string memory _doubtEye,
        uint256 _quantity
    ) public {
        distributions[_batchId].push(DistributionData(
            _distId, _capacity, _stock, _ingress, _egress, _doubtEye, _quantity, true
        ));
        emit DistributorUpdated(_batchId, _distId, _ingress, _egress, _quantity);
    }
}