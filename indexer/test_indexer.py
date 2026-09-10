"""Unit tests: decode, store rollback, and the reorg re-sync path.

stdlib unittest only -- no pytest install required. Run:
    python -m unittest test_indexer -v
"""

import unittest

from decode import decode_transfer, addr_from_topic, to_int, TRANSFER_TOPIC
from fakerpc import FakeRpc, block_hash, transfer_log
from indexer import Indexer
from store import Store

TOKEN = "0x1111111111111111111111111111111111111111"
A = "0xaa0000000000000000000000000000000000aaaa"
B = "0xbb0000000000000000000000000000000000bbbb"


class DecodeTests(unittest.TestCase):
    def test_to_int_tolerates_empty(self):
        self.assertEqual(to_int("0x"), 0)
        self.assertEqual(to_int(None), 0)
        self.assertEqual(to_int("0x10"), 16)

    def test_addr_from_topic(self):
        topic = "0x" + A[2:].rjust(64, "0")
        self.assertEqual(addr_from_topic(topic), A)

    def test_decode_erc20(self):
        d = decode_transfer(transfer_log(TOKEN, A, B, 1234, "0xtx", 2))
        self.assertEqual(d["standard"], "ERC-20")
        self.assertEqual(d["from"], A)
        self.assertEqual(d["to"], B)
        self.assertEqual(d["value"], 1234)
        self.assertEqual(d["log_index"], 2)

    def test_decode_erc721(self):
        log = {"address": TOKEN, "data": "0x",
               "topics": [TRANSFER_TOPIC,
                          "0x" + A[2:].rjust(64, "0"),
                          "0x" + B[2:].rjust(64, "0"),
                          hex(77)],
               "transactionHash": "0xtx", "logIndex": "0x0"}
        d = decode_transfer(log)
        self.assertEqual(d["standard"], "ERC-721")
        self.assertEqual(d["value"], 77)

    def test_ignores_non_transfer(self):
        self.assertIsNone(decode_transfer({"topics": ["0xdeadbeef"]}))
        self.assertIsNone(decode_transfer({"topics": []}))
        self.assertIsNone(decode_transfer(None))


class StoreTests(unittest.TestCase):
    def test_rollback_removes_blocks_and_transfers(self):
        s = Store(":memory:")
        s.insert_block(1, "0xh1", "0x0", 1, 0)
        s.insert_block(2, "0xh2", "0xh1", 2, 0)
        s.insert_transfers([(2, "0xtx", 0, TOKEN, A, B, "5", "ERC-20")])
        self.assertEqual(s.block_count(), 2)
        self.assertEqual(s.transfer_count(), 1)
        s.rollback_from(2)
        self.assertEqual(s.block_count(), 1)
        self.assertEqual(s.transfer_count(), 0)
        self.assertEqual(s.get_block_hash(1), "0xh1")
        s.close()


class ReorgTests(unittest.TestCase):
    def test_reorg_resyncs_to_canonical_chain(self):
        rpc = FakeRpc()
        rpc.build_chain(1, 5, "aa")
        rpc.logs[5] = [transfer_log(TOKEN, A, A, 5000, "0xA5", 0)]
        store = Store(":memory:")
        idx = Indexer(rpc, store, confirmations=0, start_block=1)

        first = idx.sync_once(max_blocks=5)
        self.assertEqual(first["cursor"], 5)
        self.assertEqual(store.get_block_hash(5), block_hash("aa", 5))

        # fork replaces 4,5 and extends to 6, sharing ancestor block 3
        rpc.add_block(4, block_hash("bb", 4), block_hash("aa", 3), 1004, ["0xB4"])
        rpc.add_block(5, block_hash("bb", 5), block_hash("bb", 4), 1005, ["0xB5"],
                      [transfer_log(TOKEN, B, B, 9000, "0xB5", 0)])
        rpc.add_block(6, block_hash("bb", 6), block_hash("bb", 5), 1006, ["0xB6"])

        second = idx.sync_once(max_blocks=6)
        self.assertGreaterEqual(second["reorgs"], 1)
        self.assertEqual(second["cursor"], 6)
        self.assertEqual(store.get_block_hash(4), block_hash("bb", 4))
        self.assertEqual(store.get_block_hash(6), block_hash("bb", 6))
        # orphaned transfer gone, canonical transfer present
        values = [t["value"] for t in store.recent_transfers(20)]
        self.assertNotIn("5000", values)
        self.assertIn("9000", values)
        store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
