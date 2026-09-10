"""Quadratic-funding allocation engine.

The standard Gitcoin QF subsidy for a project with contributions c_1..c_n is
    subsidy = (sum sqrt(c_i))**2 - sum c_i
and the matching pool is distributed across projects in proportion to subsidy.

The one idea this spike proves: QF's subsidy rewards the NUMBER of distinct
contributors, so an attacker who splits one budget across many wallets multiplies
their own subsidy. On a chain where every account is a verified unique human
(InterLink), that split is impossible -- one human collapses to one contributor,
and the attack evaporates. `personhood=True` models exactly that collapse.
"""

import math
from collections import defaultdict


def project_subsidy(amounts):
    """QF subsidy (matching term) for one project's list of per-contributor amounts."""
    pos = [a for a in amounts if a > 0]
    root_sum = sum(math.sqrt(a) for a in pos)
    ideal = root_sum * root_sum
    raw = sum(pos)
    return max(0.0, ideal - raw), raw


def allocate(contributions, matching_pool, personhood):
    """Distribute `matching_pool` across projects by QF subsidy.

    contributions: iterable of {"human", "wallet", "project", "amount"}.
    personhood=False -> each wallet is a distinct contributor (sybils count).
    personhood=True  -> a human's wallets collapse per project into one
                        contributor before the sqrt is taken (sybils cancel).
    Returns {project: {raw, subsidy, match, total, match_share}}.
    """
    if matching_pool < 0:
        raise ValueError("matching_pool must be non-negative")
    buckets = defaultdict(float)
    for c in contributions:
        amount = c["amount"]
        if amount <= 0:
            continue
        contributor = c["human"] if personhood else c["wallet"]
        buckets[(c["project"], contributor)] += amount

    per_project = defaultdict(list)
    for (project, _contributor), amount in buckets.items():
        per_project[project].append(amount)

    subsidy = {}
    raw = {}
    for project, amounts in per_project.items():
        subsidy[project], raw[project] = project_subsidy(amounts)

    total_subsidy = sum(subsidy.values())
    out = {}
    for project in per_project:
        share = subsidy[project] / total_subsidy if total_subsidy > 0 else 0.0
        match = matching_pool * share
        out[project] = {
            "raw": raw[project],
            "subsidy": subsidy[project],
            "match": match,
            "total": raw[project] + match,
            "match_share": share,
        }
    return out
