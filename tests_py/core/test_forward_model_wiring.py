"""Wiring tests for the B3 cerebellar forward model.

Verifies (1) default behaviour is byte-identical to the pre-B3 hierarchical
novelty scorer (include_forward_model=False), (2) opting in contributes a
non-negative forward-model corrective-error term that can only raise novelty on
a trajectory-surprising step, (3) the CORTEX_ABLATE_FORWARD_MODEL guard
reproduces the opted-out score exactly, and (4) FORWARD_MODEL is a registered,
ablatable mechanism.
"""

from __future__ import annotations

import os

from mcp_server.core.ablation import Mechanism, is_mechanism_disabled
from mcp_server.core.ablation_report import plan_full_ablation_study
from mcp_server.core.hierarchical_predictive_coding import compute_hierarchical_novelty
from mcp_server.core.predictive_coding_signals import extract_sensory_features


def _features(contents):
    return [extract_sensory_features(c) for c in contents]


# A recent history of short plain-text notes, then a step that breaks the
# trajectory (dense code + file refs + urls) — a forward-model-surprising item.
_HISTORY = ["a short plain note", "another short plain note", "yet another note"]
_SURPRISE = (
    "```python\nimport os\n```\n"
    "see /a/b/c.py and /d/e/f.py and https://example.com/x https://example.com/y"
)


class TestDefaultBehaviorPreserved:
    def test_default_is_identical_to_pre_b3(self):
        base = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), _features(_HISTORY)
        )
        explicit_off = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), _features(_HISTORY), include_forward_model=False
        )
        assert base.novelty_score == explicit_off.novelty_score
        assert base.total_free_energy == explicit_off.total_free_energy


class TestForwardModelContributes:
    def test_opt_in_raises_fe_on_surprising_step(self):
        off = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), _features(_HISTORY), include_forward_model=False
        )
        on = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), _features(_HISTORY), include_forward_model=True
        )
        # non-negative additive term -> free energy at least as high, and
        # strictly higher on this trajectory-surprising step
        assert on.total_free_energy >= off.total_free_energy
        assert on.total_free_energy > off.total_free_energy
        assert on.novelty_score >= off.novelty_score

    def test_no_history_is_noop(self):
        off = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), [], include_forward_model=False
        )
        on = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), [], include_forward_model=True
        )
        # empty trajectory -> forward-model term is 0.0 -> unchanged
        assert on.total_free_energy == off.total_free_energy
        assert on.novelty_score == off.novelty_score


class TestAblationGuard:
    def test_ablation_reproduces_opted_out_score(self):
        off = compute_hierarchical_novelty(
            _SURPRISE, ["x"], set(), _features(_HISTORY), include_forward_model=False
        )
        os.environ["CORTEX_ABLATE_FORWARD_MODEL"] = "1"
        try:
            assert is_mechanism_disabled(Mechanism.FORWARD_MODEL)
            ablated = compute_hierarchical_novelty(
                _SURPRISE, ["x"], set(), _features(_HISTORY),
                include_forward_model=True,
            )
        finally:
            del os.environ["CORTEX_ABLATE_FORWARD_MODEL"]
        # ablated opt-in == opted out, exactly
        assert ablated.total_free_energy == off.total_free_energy
        assert ablated.novelty_score == off.novelty_score
        assert not is_mechanism_disabled(Mechanism.FORWARD_MODEL)


class TestMechanismRegistered:
    def test_forward_model_in_enum(self):
        assert Mechanism.FORWARD_MODEL.value == "forward_model"

    def test_forward_model_in_full_study(self):
        study = plan_full_ablation_study()
        assert "forward_model" in study
