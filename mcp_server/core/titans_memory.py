"""Titans test-time learning memory.

source: ADR-0284
"""

from __future__ import annotations

import logging

import numpy as np
from mcp_server.core.ablation import Mechanism, is_mechanism_disabled

logger = logging.getLogger(__name__)

# Lazy torch import — only loaded when Titans memory is used
_torch = None


def _ensure_torch():
    global _torch
    if _torch is not None:
        return _torch
    try:
        import torch  # noqa: PLC0415 — source: ADR-0284

        _torch = torch
        return torch
    except ImportError:
        logger.warning("PyTorch not available — Titans memory disabled")
        return None


class TitansMemory:
    """Neural associative memory with test-time learning.

    Maintains a weight matrix M (384x384) that maps query embeddings
    to predicted memory embeddings. Updated via gradient descent after
    each retrieval.

    Args:
        dim: Embedding dimension (384 for MiniLM-L6-v2).
        eta: Momentum coefficient, decaying past surprise.
        theta: Learning rate, weighting the current gradient.
    source: ADR-0284"""

    def __init__(self, dim: int = 384, eta: float = 0.9, theta: float = 0.01):
        torch = _ensure_torch()
        if torch is None:
            self._disabled = True
            return
        self._disabled = False
        self.dim = dim
        self.eta = eta
        self.theta = theta

        # M: associative memory (linear layer, no bias)
        # Initialized as identity — predicts input unchanged
        self._M = torch.eye(dim, dtype=torch.float32, requires_grad=False)

        # S: surprise momentum (same shape as M)
        self._S = torch.zeros(dim, dim, dtype=torch.float32)

    def compute_surprise(
        self,
        query_emb: bytes | None,
        result_embs: list[bytes | None],
    ) -> float:
        """Compute surprise as gradient magnitude of associative memory loss.

        l(M; x) = ||M @ k - v||^2
        surprise = ||grad_l||_F (Frobenius norm of gradient)

        Where k = query embedding, v = mean of top result embeddings.

        Returns surprise in [0, 1] range. Returns 0.5 if inputs unavailable.
        """
        if self._disabled or not query_emb or not result_embs:
            return 0.5

        torch = _torch
        if torch is None:
            return 0.5

        # Parse embeddings
        try:
            k = torch.from_numpy(np.frombuffer(query_emb, dtype=np.float32).copy())
            vs = []
            for emb in result_embs:
                if emb is not None:
                    v = np.frombuffer(emb, dtype=np.float32)
                    if len(v) == self.dim:
                        vs.append(torch.from_numpy(v.copy()))
            if not vs:
                return 0.5

            # v = mean of result embeddings (target prediction)
            v = torch.stack(vs).mean(dim=0)

            # Compute loss: l = ||M @ k - v||^2
            M = self._M.clone().requires_grad_(True)  # noqa: N806 — source: ADR-0284
            prediction = M @ k
            loss = torch.sum((prediction - v) ** 2)

            # Compute gradient: grad_l = dl/dM
            loss.backward()
            grad = M.grad

            # Surprise = ||grad||_F normalized to [0, 1]
            # Frobenius norm of gradient, scaled by dim for normalization
            surprise_raw = torch.norm(grad, p="fro").item()
            # source: ADR-0284

            surprise = float(np.tanh(surprise_raw))

            return max(0.0, min(1.0, surprise))

        except Exception as e:  # noqa: BLE001 — source: ADR-0284
            logger.debug("Titans surprise computation failed: %s", e)
            return 0.5

    def update(
        self,
        query_emb: bytes | None,
        result_embs: list[bytes | None],
    ) -> float:
        """Update memory M and momentum S after retrieval.

        Implements the exact Titans equations:
          S_t = eta * S_{t-1} - theta * grad_l(M_{t-1}; x_t)
          M_t = M_{t-1} - S_t

        Returns the surprise value (gradient magnitude).
        """

        if is_mechanism_disabled(Mechanism.SURPRISE_MOMENTUM):
            # source: ADR-0284

            return 0.0
        if self._disabled or not query_emb or not result_embs:
            return 0.5

        torch = _torch
        if torch is None:
            return 0.5

        try:
            k = torch.from_numpy(np.frombuffer(query_emb, dtype=np.float32).copy())
            vs = []
            for emb in result_embs:
                if emb is not None:
                    v = np.frombuffer(emb, dtype=np.float32)
                    if len(v) == self.dim:
                        vs.append(torch.from_numpy(v.copy()))
            if not vs:
                return 0.5

            v = torch.stack(vs).mean(dim=0)

            # Compute gradient
            M = self._M.clone().requires_grad_(True)  # noqa: N806 — source: ADR-0284
            prediction = M @ k
            loss = torch.sum((prediction - v) ** 2)
            loss.backward()
            # backward() populates .grad on a leaf requiring grad; a None here
            # means the autograd graph was broken — surface it, don't deref None.
            grad_tensor = M.grad
            if grad_tensor is None:
                raise RuntimeError("titans surprise: gradient missing after backward()")
            grad = grad_tensor.detach()

            # Surprise momentum update: S_t = eta * S_{t-1} - theta * grad
            self._S = self.eta * self._S - self.theta * grad

            # Memory update: M_t = M_{t-1} - S_t
            self._M = self._M - self._S

            # Return surprise as gradient magnitude
            surprise_raw = torch.norm(grad, p="fro").item()
            return max(0.0, min(1.0, float(np.tanh(surprise_raw))))

        except Exception as e:  # noqa: BLE001 — source: ADR-0284
            logger.debug("Titans memory update failed: %s", e)
            return 0.5

    def reset(self) -> None:
        """Reset memory to initial state."""
        if self._disabled:
            return
        torch = _torch
        if torch is None:
            return
        self._M = torch.eye(self.dim, dtype=torch.float32, requires_grad=False)
        self._S = torch.zeros(self.dim, self.dim, dtype=torch.float32)
