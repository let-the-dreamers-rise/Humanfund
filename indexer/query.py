"""Read back the indexed data -- proof it is a queryable index, not a log tail."""

import argparse

from store import Store


def short(addr, head=8, tail=6):
    if not addr:
        return "-"
    return addr if len(addr) <= head + tail + 2 else f"{addr[:head]}...{addr[-tail:]}"


def human_value(value, standard):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return str(value)
    if standard == "ERC-721":
        return f"#{v}"
    # assume 18 decimals for display only; the raw uint256 is stored losslessly
    whole = v / 10**18
    if whole >= 0.0001:
        return f"{whole:,.4f}"
    return str(v)


def main():
    ap = argparse.ArgumentParser(description="Query the Sepolia indexer db")
    ap.add_argument("--db", default="sepolia.db")
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    store = Store(args.db)
    cursor = store.get_cursor()
    print(f"indexed head:     block {cursor}")
    print(f"blocks stored:    {store.block_count()}")
    print(f"transfers stored: {store.transfer_count()}")
    print(f"\nlatest {args.limit} transfers (real Sepolia data):")
    print(f"  {'blk':>10}  {'std':<7} {'token':<16} {'from':<16} {'to':<16} value")
    for t in store.recent_transfers(args.limit):
        print(f"  {t['block_number']:>10}  {t['standard']:<7} "
              f"{short(t['token']):<16} {short(t['from_addr']):<16} "
              f"{short(t['to_addr']):<16} {human_value(t['value'], t['standard'])}")
    store.close()


if __name__ == "__main__":
    main()
