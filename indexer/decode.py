"""ERC-20 / ERC-721 Transfer log decoding.

No web3 dependency: the Transfer event signature hash is a known constant, so we
only ever match against it and slice hex by hand. On InterLink these are the
IRC-20 / IRC-721 renamed standards; the wire format is identical.
"""

# keccak256("Transfer(address,address,uint256)") -- shared by ERC-20 and ERC-721.
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def to_int(hexstr):
    """Parse a 0x hex quantity, tolerating None and empty '0x'."""
    if hexstr is None:
        return 0
    s = hexstr.strip()
    if s in ("", "0x", "0X"):
        return 0
    return int(s, 16)


def addr_from_topic(topic):
    """A 32-byte indexed address topic -> checksum-less 0x address (last 20 bytes)."""
    t = topic[2:] if topic.lower().startswith("0x") else topic
    return "0x" + t[-40:]


def decode_transfer(log):
    """Decode one eth log into a transfer dict, or None if it is not a Transfer.

    ERC-20:  topics = [sig, from, to],           value in data
    ERC-721: topics = [sig, from, to, tokenId],  data empty
    Returns an immutable-style plain dict; caller never mutates the input log.
    """
    if not isinstance(log, dict):
        return None
    topics = log.get("topics") or []
    if not topics or topics[0].lower() != TRANSFER_TOPIC:
        return None

    base = {
        "token": (log.get("address") or "").lower(),
        "tx_hash": log.get("transactionHash"),
        "log_index": to_int(log.get("logIndex")),
        "from": None,
        "to": None,
    }
    if len(topics) == 3:
        return {**base, "standard": "ERC-20",
                "from": addr_from_topic(topics[1]), "to": addr_from_topic(topics[2]),
                "value": to_int(log.get("data"))}
    if len(topics) == 4:
        return {**base, "standard": "ERC-721",
                "from": addr_from_topic(topics[1]), "to": addr_from_topic(topics[2]),
                "value": to_int(topics[3])}
    return None
