// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AccordRegistry
/// @notice An immutable notary record of negotiation outcomes from the Accord
///         platform. This contract does NOT move funds and does NOT hold any
///         value — it only stores a permanent, publicly-readable record that
///         a negotiation happened and what terms were agreed.
///
/// Design choices explained (plain language):
/// - WRITE access is restricted to one address (the "owner" — your backend's
///   wallet). This is what makes the registry trustworthy: if anyone could
///   write a record, someone could write a fake one claiming a deal happened
///   that never did. Only your backend, which actually ran the negotiation,
///   can write.
/// - READ access is fully public. Anyone can look up a record by deal_id —
///   that's the whole point of a public, verifiable registry.
/// - We store the four plain fields (deal_id, contract_type, final_price,
///   timestamp) directly on-chain, AND a hash of those fields. Storing the
///   plain fields makes the record human-readable on a block explorer
///   without needing your database. The hash gives anyone a cheap way to
///   verify a record matches an off-chain copy (e.g. your DB row) without
///   re-uploading the whole thing.
/// - final_price is stored as an integer number of CENTS (price * 100), not
///   a float, because Solidity has no native decimal/float type. We convert
///   in the Python client before sending, and convert back when reading.
contract AccordRegistry {

    /// @notice One settled agreement, permanently stored.
    struct Agreement {
        uint256 dealId;
        string contractType;
        uint256 finalPriceCents;   // final_price * 100, as an integer
        uint256 timestamp;          // unix timestamp, seconds
        bytes32 agreementHash;      // keccak256 hash of the four fields above
        bool exists;                // true once written; lets us detect "not found"
    }

    /// @notice The only address allowed to write records (your backend's wallet).
    address public owner;

    /// @notice dealId => Agreement. One record per deal.
    mapping(uint256 => Agreement) private agreements;

    /// @notice Emitted every time a new agreement is recorded — lets anyone
    /// watch the chain for new Accord settlements without polling.
    event AgreementRecorded(
        uint256 indexed dealId,
        string contractType,
        uint256 finalPriceCents,
        uint256 timestamp,
        bytes32 agreementHash
    );

    /// @notice Restricts a function to only the owner address.
    modifier onlyOwner() {
        require(msg.sender == owner, "AccordRegistry: caller is not the owner");
        _;
    }

    /// @notice Deployer becomes the owner automatically.
    constructor() {
        owner = msg.sender;
    }

    /// @notice Record a settled negotiation outcome. Can only be called once
    /// per dealId — Accord settles each deal exactly once, so a second write
    /// attempt for the same dealId is rejected rather than silently
    /// overwriting history.
    /// @param dealId The Accord Deal's database ID.
    /// @param contractType e.g. "software_development".
    /// @param finalPriceCents The agreed price in cents (price * 100).
    /// @param timestamp Unix timestamp (seconds) when settlement occurred.
    /// @param agreementHash keccak256 hash of (dealId, contractType, finalPriceCents, timestamp),
    ///        computed off-chain in Python and passed in so on-chain and off-chain
    ///        records can be cross-checked.
    function recordAgreement(
        uint256 dealId,
        string calldata contractType,
        uint256 finalPriceCents,
        uint256 timestamp,
        bytes32 agreementHash
    ) external onlyOwner {
        require(!agreements[dealId].exists, "AccordRegistry: deal already recorded");

        agreements[dealId] = Agreement({
            dealId: dealId,
            contractType: contractType,
            finalPriceCents: finalPriceCents,
            timestamp: timestamp,
            agreementHash: agreementHash,
            exists: true
        });

        emit AgreementRecorded(dealId, contractType, finalPriceCents, timestamp, agreementHash);
    }

    /// @notice Read back a recorded agreement. Reverts if nothing was ever
    /// recorded for this dealId (cheaper and clearer than returning zeros).
    function getAgreement(uint256 dealId) external view returns (
        string memory contractType,
        uint256 finalPriceCents,
        uint256 timestamp,
        bytes32 agreementHash
    ) {
        Agreement memory a = agreements[dealId];
        require(a.exists, "AccordRegistry: no record for this dealId");
        return (a.contractType, a.finalPriceCents, a.timestamp, a.agreementHash);
    }

    /// @notice Cheap existence check — useful before calling getAgreement,
    /// or before attempting to recordAgreement, to avoid a revert.
    function isRecorded(uint256 dealId) external view returns (bool) {
        return agreements[dealId].exists;
    }

    /// @notice Transfer write access to a new backend wallet, e.g. if you
    /// rotate keys. Only the current owner can do this.
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AccordRegistry: new owner is the zero address");
        owner = newOwner;
    }
}
