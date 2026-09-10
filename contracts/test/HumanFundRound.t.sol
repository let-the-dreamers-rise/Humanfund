// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {HumanFundRound} from "../src/HumanFundRound.sol";

/// Minimal Foundry cheatcode interface (avoids a forge-std dependency).
interface Vm {
    function addr(uint256) external pure returns (address);
    function sign(uint256, bytes32) external pure returns (uint8, bytes32, bytes32);
    function deal(address, uint256) external;
    function prank(address) external;
    function expectRevert(bytes4) external;
}

contract HumanFundRoundTest {
    Vm constant vm = Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);

    uint256 constant ISSUER_PK = 0xA11CE;      // the personhood authority's key
    uint256 constant WRONG_PK = 0xBAD;         // an attacker's own key (not the issuer)
    uint256 constant POOL = 10 ether;

    address issuer;

    function setUp() public {
        issuer = vm.addr(ISSUER_PK);
        vm.deal(address(this), 1000 ether);
    }

    // sign an attestation: issuer certifies (wallet, humanId) is a verified human
    function _attest(uint256 pk, address wallet, uint256 humanId)
        internal
        pure
        returns (uint8 v, bytes32 r, bytes32 s)
    {
        bytes32 digest = keccak256(abi.encodePacked(wallet, humanId));
        (v, r, s) = vm.sign(pk, digest);
    }

    function _human(HumanFundRound round, uint256 projectId, uint256 humanId, uint256 amount) internal {
        address wallet = vm.addr(1_000_000 + humanId);
        (uint8 v, bytes32 r, bytes32 s) = _attest(ISSUER_PK, wallet, humanId);
        vm.deal(wallet, amount + 1 ether);
        vm.prank(wallet);
        round.contribute{value: amount}(projectId, humanId, v, r, s);
    }

    /// The headline: honest breadth wins, and every sybil route reverts on-chain.
    function test_honest_round_and_sybil_blocked() public {
        HumanFundRound round = new HumanFundRound{value: POOL}(issuer);
        uint256 pA = round.addProject("Clean Water Fund");
        uint256 pS = round.addProject("SybilDAO");

        // 5 distinct verified humans back Clean Water with 1 ether each
        for (uint256 h = 1; h <= 5; h++) {
            _human(round, pA, h, 1 ether);
        }

        // attacker: one verified human (id 99), wallet A1 -> one legitimate contribution
        uint256 atkId = 99;
        address a1 = vm.addr(9001);
        (uint8 v1, bytes32 r1, bytes32 s1) = _attest(ISSUER_PK, a1, atkId);
        vm.deal(a1, 5 ether);
        vm.prank(a1);
        round.contribute{value: 1 ether}(pS, atkId, v1, r1, s1);

        // route 1: a fresh wallet with NO issuer attestation (self-signed) -> revert
        address a2 = vm.addr(9002);
        (uint8 v2, bytes32 r2, bytes32 s2) = _attest(WRONG_PK, a2, 100);
        vm.deal(a2, 5 ether);
        vm.prank(a2);
        vm.expectRevert(HumanFundRound.BadAttestation.selector);
        round.contribute{value: 1 ether}(pS, 100, v2, r2, s2);

        // route 2: reuse the SAME human id 99 from wallet A1 again -> revert
        vm.deal(a1, 5 ether);
        vm.prank(a1);
        vm.expectRevert(HumanFundRound.AlreadyContributed.selector);
        round.contribute{value: 1 ether}(pS, atkId, v1, r1, s1);

        round.finalize();

        // SybilDAO has a single backer -> zero QF subsidy -> zero match
        require(round.matchOf(pS) == 0, "sybil captured match");
        // Clean Water, backed by many humans, takes the whole pool
        require(round.matchOf(pA) == POOL, "honest project underfunded");
    }

    /// Quadratic funding rewards breadth: 4 backers of 1 beat 1 backer of 4.
    function test_breadth_beats_depth() public {
        HumanFundRound round = new HumanFundRound{value: POOL}(issuer);
        uint256 broad = round.addProject("Broad");
        uint256 deep = round.addProject("Deep");

        for (uint256 h = 1; h <= 4; h++) {
            _human(round, broad, h, 1 ether);
        }
        _human(round, deep, 50, 4 ether);

        round.finalize();
        require(round.matchOf(deep) == 0, "single backer should get no subsidy");
        require(round.matchOf(broad) == POOL, "broad support should take the pool");
    }
}
