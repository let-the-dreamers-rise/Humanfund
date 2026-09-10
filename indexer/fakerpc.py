"""Deterministic in-memory RPC for tests and the reorg demo.

Mimics the RpcClient surface the Indexer uses (block_number, get_block,
get_transfer_logs) so reorg behaviour can be forced and asserted without a
network or waiting for a natural fork.
"""

from decode import TRANSFER_TOPIC

GENESIS = "0x" + "00" * 32


def block_hash(prefix, number):
    """Stable synthetic hash: 0x + 2-char prefix + zero-padded number = 64 hex."""
    return "0x" + prefix + f"{number:062x}"


def transfer_log(token, frm, to, value, tx_hash, log_index=0):
    def topic(addr):
        return "0x" + addr[2:].rjust(64, "0")
    return {
        "address": token,
        "topics": [TRANSFER_TOPIC, topic(frm), topic(to)],
        "data": hex(value),
        "transactionHash": tx_hash,
        "logIndex": hex(log_index),
    }


class FakeRpc:
    def __init__(self):
        self.blocks = {}
        self.logs = {}
        self.head = 0

    def add_block(self, number, hash, parent, timestamp=0, txs=None, transfer_logs=None):
        self.blocks[number] = {
            "number": hex(number), "hash": hash, "parentHash": parent,
            "timestamp": hex(timestamp), "transactions": txs or [],
        }
        self.logs[number] = list(transfer_logs or [])
        self.head = max(self.head, number)
        return hash

    def build_chain(self, start, count, prefix, parent0=GENESIS):
        """Append a linear chain [start .. start+count-1] with prefixed hashes."""
        parent = parent0
        for i in range(count):
            n = start + i
            h = block_hash(prefix, n)
            self.add_block(n, h, parent, timestamp=1000 + n, txs=[f"0x{n:064x}"])
            parent = h
        return self

    # RpcClient-compatible surface
    def block_number(self):
        return self.head

    def get_block(self, number, full=False):
        return self.blocks.get(number)

    def get_transfer_logs(self, number):
        return self.logs.get(number, [])
