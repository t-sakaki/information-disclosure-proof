// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title OrgSubnameRegistryV2
/// @notice A minimal, self-hosted registry that follows ENSv2's "L2 registry"
///         pattern: a fixed parent name, with individual labels registered
///         directly by their owner's wallet (label -> owner, and the reverse
///         owner -> label). This is NOT a deployment on ENS Labs' official
///         ENSv2 Namechain infrastructure -- it is our own contract, deployed
///         by this project on Base Sepolia, used only for organizations
///         (NPOs, citizen ombudsman groups, etc.) that opt in to a public,
///         human-readable name. Individual disclosure requesters are never
///         required to register here.
/// @dev    Each address may register at most one label, and each label may be
///         claimed by at most one address (first-come-first-served, no
///         admin/owner override).
contract OrgSubnameRegistryV2 {
    string public constant PARENT_NAME = "npo.disclosureproof.eth";

    mapping(bytes32 => address) public ownerOfLabel;
    mapping(address => string) public labelOfOwner;

    event SubnameRegistered(string label, address indexed owner, uint256 timestamp);

    function registerSubname(string calldata label) external {
        require(bytes(label).length > 0, "empty label");
        bytes32 key = keccak256(bytes(_toLower(label)));
        require(ownerOfLabel[key] == address(0), "label already registered");
        require(bytes(labelOfOwner[msg.sender]).length == 0, "address already has a subname");

        ownerOfLabel[key] = msg.sender;
        labelOfOwner[msg.sender] = label;
        emit SubnameRegistered(label, msg.sender, block.timestamp);
    }

    function resolve(string calldata label) external view returns (address) {
        return ownerOfLabel[keccak256(bytes(_toLower(label)))];
    }

    function reverseLabel(address owner) external view returns (string memory) {
        return labelOfOwner[owner];
    }

    /// @notice Full ENSv2-style name for an address, e.g. "sample-npo.npo.disclosureproof.eth".
    function fullName(address owner) external view returns (string memory) {
        string memory label = labelOfOwner[owner];
        if (bytes(label).length == 0) return "";
        return string.concat(label, ".", PARENT_NAME);
    }

    function _toLower(string memory s) private pure returns (string memory) {
        bytes memory b = bytes(s);
        for (uint256 i = 0; i < b.length; i++) {
            if (b[i] >= 0x41 && b[i] <= 0x5A) {
                b[i] = bytes1(uint8(b[i]) + 32);
            }
        }
        return string(b);
    }
}
