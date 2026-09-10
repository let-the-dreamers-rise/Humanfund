// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title HumanFundRound
/// @notice A sybil-proof quadratic-funding round. A contribution counts only when
/// it carries a personhood attestation signed by the trusted issuer -- on InterLink,
/// the Foundation's verified-human authority -- and each human may back a given
/// project at most once. This makes the wallet-splitting attack that breaks ordinary
/// quadratic funding impossible on-chain: an attacker cannot mint attestations, and
/// cannot reuse one human's attestation from another wallet (the wallet address is
/// signed into the attestation). Off-chain the issuer signs one attestation per real
/// human; on-chain this contract enforces one contribution per human per project.
/// @dev Spike: raw ecrecover over a packed digest. Production would use EIP-712.
contract HumanFundRound {
    address public immutable issuer;    // personhood attestation authority (InterLink)
    address public immutable operator;  // funds the pool, adds projects, finalizes
    uint256 public matchingPool;
    bool public finalized;

    struct Project {
        string name;
        uint256 sumContrib;   // sum of contributions
        uint256 sumSqrt;      // sum of sqrt(contribution), one term per human
        uint256 matchAmount;  // set at finalize
        bool exists;
    }
    uint256 public projectCount;
    mapping(uint256 => Project) public projects;
    mapping(bytes32 => bool) public contributed; // one per (project, human)

    event ProjectAdded(uint256 indexed id, string name);
    event Contributed(uint256 indexed projectId, uint256 indexed humanId, address wallet, uint256 amount);
    event Finalized(uint256 totalSubsidy, uint256 pool);

    error NotOperator();
    error BadAttestation();
    error AlreadyContributed();
    error RoundFinalized();
    error NothingToFinalize();
    error NoProject();
    error ZeroValue();

    constructor(address _issuer) payable {
        issuer = _issuer;
        operator = msg.sender;
        matchingPool = msg.value;
    }

    function addProject(string calldata name) external returns (uint256 id) {
        if (msg.sender != operator) revert NotOperator();
        id = projectCount++;
        projects[id] = Project(name, 0, 0, 0, true);
        emit ProjectAdded(id, name);
    }

    /// @notice Contribute to a project with a personhood attestation.
    /// @param projectId the project to back
    /// @param humanId the issuer-assigned id of the verified human
    /// @param v,r,s issuer's signature over keccak256(msg.sender, humanId)
    function contribute(uint256 projectId, uint256 humanId, uint8 v, bytes32 r, bytes32 s)
        external
        payable
    {
        if (finalized) revert RoundFinalized();
        if (msg.value == 0) revert ZeroValue();
        Project storage p = projects[projectId];
        if (!p.exists) revert NoProject();

        // personhood gate: only an address the issuer attested as a verified human
        bytes32 digest = keccak256(abi.encodePacked(msg.sender, humanId));
        if (ecrecover(digest, v, r, s) != issuer) revert BadAttestation();

        // uniqueness gate: one human backs a project once (no wallet-splitting)
        bytes32 key = keccak256(abi.encodePacked(projectId, humanId));
        if (contributed[key]) revert AlreadyContributed();
        contributed[key] = true;

        p.sumContrib += msg.value;
        p.sumSqrt += _sqrt(msg.value);
        emit Contributed(projectId, humanId, msg.sender, msg.value);
    }

    /// @notice Distribute the pool by quadratic-funding subsidy.
    /// subsidy_p = sumSqrt_p^2 - sumContrib_p ; pool split pro-rata to subsidy.
    function finalize() external {
        if (msg.sender != operator) revert NotOperator();
        if (finalized) revert RoundFinalized();
        uint256 n = projectCount;
        uint256[] memory subs = new uint256[](n);
        uint256 totalSubsidy;
        for (uint256 i = 0; i < n; i++) {
            Project storage p = projects[i];
            uint256 ideal = p.sumSqrt * p.sumSqrt;
            uint256 sub = ideal > p.sumContrib ? ideal - p.sumContrib : 0;
            subs[i] = sub;
            totalSubsidy += sub;
        }
        if (totalSubsidy == 0) revert NothingToFinalize();
        for (uint256 i = 0; i < n; i++) {
            projects[i].matchAmount = (matchingPool * subs[i]) / totalSubsidy;
        }
        finalized = true;
        emit Finalized(totalSubsidy, matchingPool);
    }

    function matchOf(uint256 id) external view returns (uint256) {
        return projects[id].matchAmount;
    }

    /// @dev Integer square root (Babylonian method).
    function _sqrt(uint256 x) internal pure returns (uint256 y) {
        if (x == 0) return 0;
        uint256 z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }
}
