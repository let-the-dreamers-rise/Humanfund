"""The indexer: ingest blocks forward, decode transfers, and stay reorg-safe.

Reorg detection is the whole point. Before ingesting block N we require
block[N].parentHash == stored hash of block N-1. On mismatch we roll the tip
back one block at a time until we find the common ancestor, then re-sync the
canonical chain. This is exactly the guarantee milestone M1 promises the grant.
"""

import argparse

from decode import decode_transfer, to_int
from rpc import RpcClient
from store import Store


class Indexer:
    def __init__(self, rpc, store, confirmations=5, start_block=None):
        self.rpc = rpc
        self.store = store
        self.confirmations = max(0, confirmations)
        self.start_block = start_block

    def _ingest(self, number, blk):
        rows = []
        for log in self.rpc.get_transfer_logs(number):
            d = decode_transfer(log)
            if d:
                rows.append((number, d["tx_hash"], d["log_index"], d["token"],
                             d["from"], d["to"], str(d["value"]), d["standard"]))
        self.store.insert_block(
            number=number, hash=blk["hash"], parent=blk.get("parentHash"),
            ts=to_int(blk.get("timestamp")), tx_count=len(blk.get("transactions") or []),
        )
        self.store.insert_transfers(rows)
        return len(rows)

    def sync_once(self, max_blocks=20, on_event=None):
        head = self.rpc.block_number() - self.confirmations
        cursor = self.store.get_cursor()
        if cursor is None:
            start = self.start_block if self.start_block is not None else max(0, head - max_blocks + 1)
            cursor = start - 1
        added = transfers = reorgs = 0
        guard = 0
        limit = max_blocks * 4 + 8
        while added < max_blocks and cursor < head and guard < limit:
            guard += 1
            n = cursor + 1
            blk = self.rpc.get_block(n, False)
            if not blk:
                break
            prev_hash = self.store.get_block_hash(cursor)
            parent = blk.get("parentHash")
            if prev_hash is not None and parent is not None and parent.lower() != prev_hash.lower():
                if on_event:
                    on_event("reorg", {"height": cursor, "stored": prev_hash, "parent_seen": parent})
                self.store.rollback_from(cursor)
                self.store.set_cursor(cursor - 1)
                cursor -= 1
                reorgs += 1
                continue
            t = self._ingest(n, blk)
            self.store.set_cursor(n)
            if on_event:
                on_event("block", {"height": n, "hash": blk["hash"], "transfers": t})
            cursor = n
            transfers += t
            added += 1
        return {"head": head, "cursor": cursor, "blocks_added": added,
                "transfers": transfers, "reorgs": reorgs}


def main():
    ap = argparse.ArgumentParser(description="Reorg-safe Sepolia ERC-20 indexer spike")
    ap.add_argument("--live", action="store_true", help="index against live Sepolia RPC")
    ap.add_argument("--blocks", type=int, default=12, help="max blocks to ingest this run")
    ap.add_argument("--confirmations", type=int, default=5, help="stay this far behind head")
    ap.add_argument("--start", type=int, default=None, help="start block (default: recent window)")
    ap.add_argument("--db", default="sepolia.db", help="sqlite path")
    args = ap.parse_args()
    if not args.live:
        print("pass --live to index against Sepolia. See reorg_demo.py for the reorg proof.")
        return

    rpc = RpcClient()
    store = Store(args.db)
    idx = Indexer(rpc, store, confirmations=args.confirmations, start_block=args.start)

    def show(kind, info):
        if kind == "block":
            print(f"  + block {info['height']:>10}  {info['hash'][:14]}...  "
                  f"{info['transfers']:>3} transfers")
        else:
            print(f"  ! reorg at height {info['height']} -> rolling back")

    print(f"indexing up to {args.blocks} blocks (staying {args.confirmations} behind head)")
    summary = idx.sync_once(max_blocks=args.blocks, on_event=show)
    print(f"\nchain head (safe):   {summary['head']}")
    print(f"indexed to block:    {summary['cursor']}")
    print(f"blocks this run:     {summary['blocks_added']}")
    print(f"transfers decoded:   {summary['transfers']}")
    print(f"reorgs handled:      {summary['reorgs']}")
    print(f"totals in db:        {store.block_count()} blocks, {store.transfer_count()} transfers")
    store.close()


if __name__ == "__main__":
    main()
