"""Minimal, dependency-free JSON-RPC client with endpoint failover.

Swapping the endpoint list for an InterLink Taj Mahal RPC is the only change
needed to point this indexer at the real chain -- that is milestone M1.
"""

import json
import time
import urllib.error
import urllib.request

from decode import TRANSFER_TOPIC

DEFAULT_ENDPOINTS = [
    "https://ethereum-sepolia-rpc.publicnode.com",
    "https://1rpc.io/sepolia",
    "https://rpc.sepolia.org",
]


class RpcError(Exception):
    """Raised when every endpoint fails or the node returns a JSON-RPC error."""


class RpcClient:
    def __init__(self, endpoints=None, timeout=20, retries=3, backoff=1.5):
        self.endpoints = list(endpoints or DEFAULT_ENDPOINTS)
        if not self.endpoints:
            raise ValueError("at least one RPC endpoint is required")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._id = 0

    def call(self, method, params=None):
        if not method:
            raise ValueError("method is required")
        self._id += 1
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or []}
        ).encode()
        last = None
        for attempt in range(self.retries):
            for ep in self.endpoints:
                try:
                    req = urllib.request.Request(
                        ep, data=payload,
                        headers={"Content-Type": "application/json",
                                 "User-Agent": "humanscan-indexer/0.1",
                                 "Accept": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        body = json.loads(resp.read().decode())
                    err = body.get("error")
                    if err:
                        last = RpcError(f"{method}: {err}")
                        continue
                    return body.get("result")
                except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                    last = exc
                    continue
            time.sleep(self.backoff * (attempt + 1))
        raise RpcError(f"all endpoints failed for {method}: {last}")

    # --- convenience wrappers -------------------------------------------------
    def block_number(self):
        return int(self.call("eth_blockNumber"), 16)

    def get_block(self, number, full=False):
        return self.call("eth_getBlockByNumber", [hex(number), bool(full)])

    def get_transfer_logs(self, number):
        return self.call(
            "eth_getLogs",
            [{"fromBlock": hex(number), "toBlock": hex(number), "topics": [TRANSFER_TOPIC]}],
        ) or []
