"""Build a realistic funding round + a sybil attacker, deterministically.

Three honest projects funded by many distinct humans giving small amounts, plus
one attacker who controls a single budget. In the no-personhood world the
attacker splits that budget across many wallets; on InterLink the attacker is one
human and the split is impossible.
"""

import random

HONEST_PROJECTS = [
    ("Clean Water Fund", 42, 3, 14),    # (name, donors, min$, max$)
    ("Open Textbooks", 28, 2, 20),
    ("Village Solar", 17, 5, 25),
]
ATTACKER_PROJECT = "SybilDAO"


def build_round(seed=7, attacker_budget=100.0, attacker_wallets=150):
    """Return (contributions, attacker_budget). One contribution per (wallet, project).

    Honest donors are distinct humans with one wallet each, so personhood mode
    leaves them untouched. The attacker has one human id and many wallet ids, each
    putting an equal slice of the budget into SybilDAO.
    """
    rng = random.Random(seed)
    contributions = []
    for name, donors, lo, hi in HONEST_PROJECTS:
        for i in range(donors):
            who = f"human_{name[:4].lower()}_{i}"
            contributions.append({
                "human": who, "wallet": who, "project": name,
                "amount": float(rng.randint(lo, hi)),
            })
    slice_amt = attacker_budget / attacker_wallets
    for w in range(attacker_wallets):
        contributions.append({
            "human": "attacker", "wallet": f"sybil_wallet_{w}",
            "project": ATTACKER_PROJECT, "amount": slice_amt,
        })
    return contributions, attacker_budget
