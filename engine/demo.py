"""Run one funding round with and without personhood, and print the receipt.

The attacker spends the SAME $100 in both worlds. The only difference is whether
the chain lets one human pretend to be a hundred contributors.
"""

from qf import allocate
from round import build_round, ATTACKER_PROJECT

POOL = 10_000.0


def pct(x):
    return f"{x * 100:5.1f}%"


def money(x):
    return f"${x:,.0f}"


def main():
    ATTACKER_WALLETS = 150
    contributions, budget = build_round(attacker_budget=100.0, attacker_wallets=ATTACKER_WALLETS)
    off = allocate(contributions, POOL, personhood=False)
    on = allocate(contributions, POOL, personhood=True)
    projects = sorted(off, key=lambda p: off[p]["match"], reverse=True)

    print(f"Quadratic funding round  |  matching pool {money(POOL)}  |  "
          f"attacker budget {money(budget)} across {ATTACKER_WALLETS} wallets\n")
    header = f"  {'project':<18} {'raw $':>8} | {'MATCH no-PoH':>12} {'share':>7} | {'MATCH InterLink':>15} {'share':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for p in projects:
        tag = "  <- attacker" if p == ATTACKER_PROJECT else ""
        print(f"  {p:<18} {off[p]['raw']:>8.0f} | "
              f"{money(off[p]['match']):>12} {pct(off[p]['match_share']):>7} | "
              f"{money(on[p]['match']):>15} {pct(on[p]['match_share']):>7}{tag}")

    a_off = off[ATTACKER_PROJECT]
    a_on = on[ATTACKER_PROJECT]
    print("\n  RESULT")
    print("  " + "-" * 60)
    print(f"  Without personhood: a {money(budget)} attacker captured "
          f"{money(a_off['match'])} of the {money(POOL)} pool "
          f"({pct(a_off['match_share'])}) --")
    print(f"                      more than any of the honestly-funded projects.")
    print(f"  With InterLink:     the same {money(budget)} attacker captured "
          f"{money(a_on['match'])} ({pct(a_on['match_share'])}).")
    mult = (a_off["match"] / a_on["match"]) if a_on["match"] > 1e-9 else float("inf")
    factor = "infinite" if mult == float("inf") else f"{mult:,.0f}x"
    print(f"  Personhood shrank the attack by {factor}. Same money, one human, no split.")


if __name__ == "__main__":
    main()
