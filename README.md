# HumanFund

Sybil-proof quadratic funding for a chain of verified humans. Quadratic funding is the
gold-standard way to allocate community money fairly &mdash; breadth of support beats size of
wallet &mdash; but it has one decade-old flaw: split one budget across many wallets and you
multiply your own match. Gitcoin and Human Passport spend millions patching this and still
leak. On a chain where every account is already a verified unique human, the defense is
**free and structural**: an attacker cannot be a hundred people.

HumanFund is that allocator, built for [InterLink](https://interlinklabs.ai). Customer zero
is the Foundation's own Phase 3 builder-grant round.

## The proof, not the pitch

| What | Where |
|------|-------|
| Interactive demo (drag the sybil attack, flip personhood, watch it collapse) | https://claude.ai/code/artifact/99290bfa-a165-4a85-b7db-1b9995b0db97 |
| Grant proposal | https://claude.ai/code/artifact/b11b2d4e-00ec-46b4-86e7-367bcc2e5e64 &middot; [`proposal.html`](proposal.html) |
| Round contract, source-verified, with a full round's events | [`0x14fbF62C…0A67`](https://sepolia.etherscan.io/address/0x14fbF62C2eEAC774515F1301e84d9611197d0A67) |

### A complete sybil-proof round, executed on-chain (Sepolia)

One round ran end-to-end against a 0.02 ETH matching pool:

| Project | Backers | Raised | Match |
|---------|---------|--------|-------|
| Clean Water Coalition | 2 humans | 0.002 ETH | **0.02 ETH (whole pool)** |
| SybilDAO | 1 human | 0.004 ETH | **0.0 ETH** |

The project that raised **twice the money** received **nothing**, because it had one human
behind it &mdash; and the attempt to forge a second backer was **rejected on-chain**:

- Finalize (the pool split): [`0x0d85a02f…d59810`](https://sepolia.etherscan.io/tx/0x0d85a02f3003dfa6c02f129a3eabf82adece6b2af4ba2d164158d1cd37d59810)
- Sybil, forged attestation, reverted (status 0): [`0x41c7c881…4fe42d`](https://sepolia.etherscan.io/tx/0x41c7c881fa28c0c8eb4d5b07e1177e9a2234e5e251addeecfb159b1c714fe42d)

Every transaction hash is in [`contracts/round-receipts.json`](contracts/round-receipts.json).

## Layout

| Path | What it is |
|------|-----------|
| [`contracts/`](contracts) | `HumanFundRound.sol` &mdash; the sybil-proof QF round as a real contract (personhood gate + uniqueness gate + on-chain quadratic matching), Foundry tests, and the scripts that ran the live round |
| [`engine/`](engine) | the quadratic-funding engine in pure-stdlib Python with its test suite, and the interactive demo page |
| [`indexer/`](indexer) | a reorg-safe EVM indexer (stdlib only) that tracks contributions and eligibility; points at InterLink with a one-line change |
| [`proposal.html`](proposal.html) | the grant proposal |

## Run it

```bash
# QF engine + tests
cd engine && python -m unittest -v && python demo.py

# Contract tests (Foundry)
cd contracts && forge test -vv

# Re-run the full on-chain round (needs a funded testnet key in .deployer.json)
cd contracts && node round.cjs
```

## How the sybil defense works

A contribution counts only when it carries a personhood attestation signed by a trusted
issuer (on InterLink, the Foundation's verified-human authority), and each human may back a
given project at most once. The wallet address is signed into the attestation, so it cannot
be reused from another wallet. An attacker cannot mint attestations and cannot split one
human into many &mdash; so the wallet-splitting attack that breaks ordinary quadratic funding is
impossible. `issuer` is the only integration point: set it to InterLink's attestation
authority and the same contract runs there unchanged.

## License

MIT.
