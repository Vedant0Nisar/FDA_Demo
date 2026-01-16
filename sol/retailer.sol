// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RetailerRegistry {
    struct RetailerData {
        string retailerId;
        string retailerType;
        string shopName;
        uint256 quantityPurchased;
        string ownerName;
        string contactNo;
        string registrationDate;
        bool exists;
    }

    mapping(string => RetailerData) public retailerLedger;
    event RetailerUpdated(string indexed batchId, string shopName, string ownerName);

    function updateRetailer(
        string memory _batchId,
        string memory _retailerId,
        string memory _retailerType,
        string memory _shopName,
        uint256 _quantity,
        string memory _ownerName,
        string memory _contactNo,
        string memory _regDate
    ) public {
        retailerLedger[_batchId] = RetailerData(
            _retailerId, _retailerType, _shopName, _quantity, _ownerName, _contactNo, _regDate, true
        );
        emit RetailerUpdated(_batchId, _shopName, _ownerName);
    }
}