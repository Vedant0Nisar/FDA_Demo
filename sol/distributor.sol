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
        bool exists;
    }

    mapping(string => DistributionData) public distributions;
    event DistributorUpdated(string indexed batchId, string distId, string ingress, string egress);

    function updateDistributor(
        string memory _batchId,
        string memory _distId,
        string memory _capacity,
        string memory _stock,
        string memory _ingress,
        string memory _egress,
        string memory _doubtEye
    ) public {
        distributions[_batchId] = DistributionData(
            _distId, _capacity, _stock, _ingress, _egress, _doubtEye, true
        );
        emit DistributorUpdated(_batchId, _distId, _ingress, _egress);
    }
}