"""Tests: QF formula correctness, sybil amplification, and personhood neutralising it.

stdlib unittest only:  python -m unittest test_qf -v
"""

import unittest

from qf import project_subsidy, allocate
from round import build_round, ATTACKER_PROJECT


class FormulaTests(unittest.TestCase):
    def test_two_equal_contributors(self):
        # (sqrt1 + sqrt1)^2 - 2 = 4 - 2 = 2
        sub, raw = project_subsidy([1.0, 1.0])
        self.assertAlmostEqual(sub, 2.0)
        self.assertAlmostEqual(raw, 2.0)

    def test_single_contributor_has_no_subsidy(self):
        # one $100 gift: (sqrt100)^2 - 100 = 0
        sub, raw = project_subsidy([100.0])
        self.assertAlmostEqual(sub, 0.0)
        self.assertAlmostEqual(raw, 100.0)

    def test_breadth_beats_depth(self):
        # 100 people giving $1 out-subsidise 1 person giving $100
        broad, _ = project_subsidy([1.0] * 100)
        deep, _ = project_subsidy([100.0])
        self.assertGreater(broad, deep)
        self.assertAlmostEqual(broad, 100.0 * 100.0 - 100.0)  # 9900


class PersonhoodTests(unittest.TestCase):
    def setUp(self):
        self.contribs, _ = build_round(attacker_budget=100.0, attacker_wallets=150)

    def test_split_amplifies_without_personhood(self):
        off = allocate(self.contribs, 10_000.0, personhood=False)
        # 100 wallets of $1 -> subsidy ~ 9900
        self.assertGreater(off[ATTACKER_PROJECT]["subsidy"], 5_000.0)

    def test_personhood_neutralises_the_split(self):
        on = allocate(self.contribs, 10_000.0, personhood=True)
        # one human, $100, one contribution -> subsidy 0
        self.assertLess(on[ATTACKER_PROJECT]["subsidy"], 1e-6)
        self.assertLess(on[ATTACKER_PROJECT]["match"], 1e-6)

    def test_attacker_share_collapses(self):
        off = allocate(self.contribs, 10_000.0, personhood=False)
        on = allocate(self.contribs, 10_000.0, personhood=True)
        self.assertGreater(off[ATTACKER_PROJECT]["match_share"], 0.30)
        self.assertLess(on[ATTACKER_PROJECT]["match_share"], 0.001)

    def test_honest_projects_gain_under_personhood(self):
        off = allocate(self.contribs, 10_000.0, personhood=False)
        on = allocate(self.contribs, 10_000.0, personhood=True)
        honest = [p for p in off if p != ATTACKER_PROJECT]
        off_total = sum(off[p]["match"] for p in honest)
        on_total = sum(on[p]["match"] for p in honest)
        # money the attacker vacated flows to the real projects
        self.assertGreater(on_total, off_total)


if __name__ == "__main__":
    unittest.main(verbosity=2)
