# HumanFund Spike (working name)

Proof of the one claim behind the InterLink funding/allocation direction:
**a chain of verified unique humans makes quadratic funding sybil-proof for free.**

Quadratic funding (Gitcoin's mechanism) matches projects by the number of distinct
contributors, so its known weakness is wallet-splitting: one attacker with $100
split across 100 wallets multiplies their own matching subsidy. Gitcoin and Human
Passport spend millions approximating sybil defense to patch this. On InterLink,
one-human-one-node makes the split impossible -- the attack cancels itself.

This is not a pitch. It is a correct QF engine (stdlib only) that runs a real
round twice -- once counting wallets, once counting humans -- and prints the gap.

## Run it

```bash
python demo.py                     # the receipt: attacker capture with vs without personhood
python -m unittest test_qf -v      # QF formula + sybil amplification + neutralisation
```

## Files

| File | Role |
|------|------|
| `qf.py` | QF subsidy + matching-pool allocation; `personhood` collapses a human's wallets |
| `round.py` | A deterministic round: 3 honestly-funded projects + one sybil attacker |
| `demo.py` | Runs the round with and without personhood, prints the comparison |
| `test_qf.py` | Formula correctness and the sybil-neutralisation guarantee |

## Why the grantor funds it

Customer zero is the Foundation itself: InterLink is about to distribute Phase 3
builder grants. This is the sybil-proof rail those grants run on -- a funding round
where one-human-one-vote actually holds, which is impossible anywhere sybils are
cheap and is free on a chain of verified humans. It reuses the live-tested
[Sepolia indexer](../sepolia-indexer/README.md) to track contributions.
