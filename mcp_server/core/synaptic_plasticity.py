"""Synaptic plasticity — public API facade.

source: ADR-0275"""

from __future__ import annotations

from mcp_server.core.synaptic_plasticity_hebbian import (
    apply_hebbian_update,
    apply_stdp_batch,
    compute_bcm_phi,
    compute_ltd,
    compute_ltp,
    compute_stdp_update,
    update_bcm_threshold,
)
from mcp_server.core.synaptic_plasticity_stochastic import (
    apply_stochastic_hebbian_update,
)
from mcp_server.core.synaptic_plasticity_stp import (
    SynapticState,
    compute_effective_release_probability,
    compute_noisy_weight_update,
    phase_modulate_plasticity,
    stochastic_transmit,
    update_short_term_dynamics,
)

__all__ = [
    "SynapticState",
    "compute_effective_release_probability",
    "stochastic_transmit",
    "update_short_term_dynamics",
    "compute_noisy_weight_update",
    "phase_modulate_plasticity",
    "compute_bcm_phi",
    "compute_ltp",
    "compute_ltd",
    "update_bcm_threshold",
    "apply_hebbian_update",
    "compute_stdp_update",
    "apply_stdp_batch",
    "apply_stochastic_hebbian_update",
]
