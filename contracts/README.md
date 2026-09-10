# HumanFund Round Contracts

The on-chain half of [HumanFund](../humanfund-proposal.html): a **sybil-proof
quadratic-funding round as a real smart contract**, not a simulation. This is the
"can this builder actually ship the hard part" proof for grant milestone **M1**.

`HumanFundRound.sol` enforces, on-chain:

1. **Personhood gate** — a contribution counts only with an attestation signed by the
   trusted issuer (on InterLink, the Foundation's verified-human authority). The wallet
   address is signed into the attestation, so it can't be reused elsewhere.
2. **Uniqueness gate** — each human backs a project at most once, so the wallet-splitting
   attack that breaks ordinary quadratic funding is impossible.
3. **Quadratic matching** — on `finalize()`, the pool is split by
   `subsidy = (Σ√cᵢ)² − Σcᵢ`, computed with an on-chain integer square root.

## Run it

```bash
# Foundry (installed at ~/.foundry/bin — shadowed on PATH by Atlassian's `forge`)
~/.foundry/bin/forge.exe test -vv
```

Result:

```
[PASS] test_breadth_beats_depth()              4 backers of 1 beat 1 backer of 4
[PASS] test_honest_round_and_sybil_blocked()   sybil routes revert; SybilDAO match = 0
2 passed; 0 failed
```

The sybil test proves three things on a real EVM: an un-attested wallet reverts
(`BadAttestation`), reusing one human's id from another wallet reverts
(`AlreadyContributed`), and after `finalize()` a single-backer attacker project receives
**zero** match while the many-human project takes the whole pool.

## Live on Sepolia

Two source-verified instances (Sourcify, exact runtime + creation match), identical bytecode:

- **Verified source, empty:** [`0x1e0Dd67D…7660`](https://sepolia.etherscan.io/address/0x1e0Dd67D678bb7Ff269B3945a0A0E501b9727660)
- **A full round, executed end-to-end:** [`0x14fbF62C…0A67`](https://sepolia.etherscan.io/address/0x14fbF62C2eEAC774515F1301e84d9611197d0A67)

On the second instance a complete sybil-proof round ran on-chain with a 0.02 ETH matching pool:

| Project | Backers | Raised | Match |
|---------|---------|--------|-------|
| Clean Water Coalition | 2 humans | 0.002 ETH | **0.02 ETH (whole pool)** |
| SybilDAO | 1 human | 0.004 ETH | **0.0 ETH** |

The project that raised **twice the money** received **nothing** — quadratic funding rewards
breadth of humans over size of wallet — and the attempt to fake a second backer was rejected
on-chain:

- Finalize: [`0x0d85a02f…d59810`](https://sepolia.etherscan.io/tx/0x0d85a02f3003dfa6c02f129a3eabf82adece6b2af4ba2d164158d1cd37d59810)
- Sybil, forged attestation, reverted (status 0, 32k gas — an early `BadAttestation` guard, not gas exhaustion): [`0x41c7c881…4fe42d`](https://sepolia.etherscan.io/tx/0x41c7c881fa28c0c8eb4d5b07e1177e9a2234e5e251addeecfb159b1c714fe42d)

Every tx hash is in `round-receipts.json`. A reviewer can read the verified source and scroll
the round's events directly on Etherscan. Re-run the whole round with `node round.cjs`.

## Pointing at InterLink

`issuer` is the only integration point: set it to the Foundation's attestation authority
and the same contract runs on InterLink unchanged (IRC-20/native value; identical EVM).
The Sepolia round above already proves the mechanism end-to-end on a public chain.

## Files

| File | Role |
|------|------|
| `src/HumanFundRound.sol` | the sybil-proof QF round contract |
| `test/HumanFundRound.t.sol` | Foundry tests: honest round, sybil rejection, breadth-beats-depth |
| `foundry.toml` | Foundry config (no external deps) |
| `round.cjs` | executes one full sybil-proof round on Sepolia and writes receipts |
| `round-receipts.json` | every tx hash + the final pool split from the live round |
| `read.cjs` | reads a deployed instance's live state |
