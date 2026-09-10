"""Runnable, narrated proof of reorg safety -- no network, fully deterministic.

We index a canonical chain, then a competing fork that reorgs the last two
blocks, and show the indexer detect it, roll back the orphaned blocks and their
transfers, and re-sync the winning chain. This is the milestone-M1 guarantee
made visible in ~1 second.
"""

from fakerpc import FakeRpc, block_hash, transfer_log
from indexer import Indexer
from store import Store

TOKEN = "0x1111111111111111111111111111111111111111"
A = "0xaa000000000000000000000000000000000000a1"
B = "0xbb000000000000000000000000000000000000b2"


def line():
    print("-" * 66)


def main():
    rpc = FakeRpc()
    # Canonical chain A: blocks 1..5. Block 5 carries an ERC-20 transfer.
    rpc.build_chain(1, 5, "aa")
    rpc.logs[5] = [transfer_log(TOKEN, A, A, 5_000, "0xA5", 0)]

    store = Store(":memory:")
    idx = Indexer(rpc, store, confirmations=0, start_block=1)

    print("STEP 1  index canonical chain A (blocks 1-5)")
    line()
    s1 = idx.sync_once(max_blocks=5,
                       on_event=lambda k, i: print(f"  + block {i['height']} {i['hash'][:10]}... "
                                                   f"{i.get('transfers',0)} transfers") if k == "block" else None)
    print(f"  tip = block {s1['cursor']}  hash {store.get_block_hash(5)[:10]}...")
    print(f"  blocks={store.block_count()} transfers={store.transfer_count()} "
          f"(A5 transfer of 5,000 present)")
    print()

    # A fork appears: blocks 4',5' with different hashes (prefix bb), plus a new 6'.
    # They share ancestor block 3 (parent of 4' == hash of A3).
    parent3 = block_hash("aa", 3)
    rpc.add_block(4, block_hash("bb", 4), parent3, timestamp=1004, txs=["0xB4"])
    rpc.add_block(5, block_hash("bb", 5), block_hash("bb", 4), timestamp=1005, txs=["0xB5"],
                  transfer_logs=[transfer_log(TOKEN, B, B, 9_000, "0xB5", 0)])
    rpc.add_block(6, block_hash("bb", 6), block_hash("bb", 5), timestamp=1006, txs=["0xB6"])

    print("STEP 2  fork wins: 4',5',6' replace 4,5 (common ancestor = block 3)")
    line()
    s2 = idx.sync_once(
        max_blocks=6,
        on_event=lambda k, i: print(
            f"  ! REORG detected at height {i['height']}: stored {i['stored'][:10]}... "
            f"!= parent {i['parent_seen'][:10]}...  -> rollback"
        ) if k == "reorg" else print(f"  + block {i['height']} {i['hash'][:10]}... "
                                     f"{i.get('transfers',0)} transfers"),
    )
    print()
    print("STEP 3  result")
    line()
    print(f"  reorgs handled:   {s2['reorgs']}")
    print(f"  tip = block {s2['cursor']}  hash {store.get_block_hash(6)[:10]}... (bb chain)")
    print(f"  block 4 hash now: {store.get_block_hash(4)[:10]}...  "
          f"({'bb fork' if store.get_block_hash(4).startswith('0xbb') else 'STILL aa -- BUG'})")
    remaining = [t for t in store.recent_transfers(10)]
    a5 = [t for t in remaining if t["value"] == "5000"]
    b5 = [t for t in remaining if t["value"] == "9000"]
    print(f"  orphaned A5 transfer (5,000) removed: {'yes' if not a5 else 'NO -- BUG'}")
    print(f"  canonical B5 transfer (9,000) present: {'yes' if b5 else 'NO -- BUG'}")
    line()
    ok = s2["reorgs"] >= 1 and not a5 and b5 and store.get_block_hash(4).startswith("0xbb")
    print("REORG SAFETY:", "PASS" if ok else "FAIL")
    store.close()


if __name__ == "__main__":
    main()
