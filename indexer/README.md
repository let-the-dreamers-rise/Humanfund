# Sepolia Indexer Spike

Proof of the hard part behind [HumanScan](../humanscan.html): a real, reorg-safe
EVM indexer. It connects to a live Sepolia node, ingests blocks, decodes ERC-20
and ERC-721 `Transfer` logs into a queryable SQLite index, and rolls back cleanly
when the chain reorganises.

The HumanScan demo proved the UI. This proves the indexer -- the exact capability
grant **milestone M1** buys. Pointing it at InterLink is a one-line change: swap
the RPC endpoints in `rpc.py` for a Taj Mahal endpoint. IRC-20 / IRC-721 use the
same `Transfer` wire format, so `decode.py` is unchanged.

## Zero dependencies

Python 3.11+ standard library only -- `urllib` for JSON-RPC, `sqlite3` for storage.
No `web3`, no `pip install`. The `Transfer` event hash is a known constant, so no
keccak library is needed to match and decode it.

## Run it

```bash
# Index recent real Sepolia blocks into sepolia.db
python indexer.py --live --blocks 12

# Read the indexed data back
python query.py --db sepolia.db

# Watch reorg safety happen, deterministically, with no network
python reorg_demo.py

# Tests (decode + store rollback + reorg re-sync)
python -m unittest test_indexer -v
```

## Layout

| File | Role |
|------|------|
| `rpc.py` | JSON-RPC client with endpoint failover (the only InterLink swap point) |
| `decode.py` | ERC-20 / ERC-721 `Transfer` log decoding, no web3 |
| `store.py` | SQLite repository; `rollback_from()` is the reorg-safety primitive |
| `indexer.py` | Forward sync + parent-hash reorg detection and rollback |
| `query.py` | Read the index back |
| `fakerpc.py` | Deterministic in-memory chain for tests and the demo |
| `reorg_demo.py` | Narrated, runnable reorg proof |
| `test_indexer.py` | Unit tests |

## How reorg safety works

Before ingesting block `N`, the indexer requires `block[N].parentHash` to equal the
stored hash of block `N-1`. On mismatch it deletes the orphaned tip, steps back one
block, and repeats until it finds the common ancestor -- then re-syncs the winning
chain. Orphaned transfers are removed with their block. A `confirmations` lag keeps
the indexer a few blocks behind head to make reorgs rare in the first place, but
they are handled correctly when they do occur.
