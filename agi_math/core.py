"""
Active Inference / Free Energy minimization core.

Discrete POMDP formulation:

    P(o | s, a) = A[a, o, s]            likelihood (observation model)
    P(s' | s, a) = B[a, s', s]          transition (dynamics model)
    log P~(o) = C[o]                    log preferences over observations
    P(s_0) = D[s]                       prior over hidden states

The agent maintains an approximate posterior Q(s) and acts to minimize
Expected Free Energy:

    G(a) = - pragmatic_value(a) - epistemic_value(a)

where pragmatic_value pulls predicted observations toward preferences C,
and epistemic_value rewards information gain (uncertainty reduction).
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-16


def softmax(x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    x = np.asarray(x, dtype=float) / temperature
    x = x - np.max(x)
    e = np.exp(x)
    return e / e.sum()


def normalize(x: np.ndarray, axis: int | None = None) -> np.ndarray:
    x = np.asarray(x, dtype=float) + _EPS
    return x / x.sum(axis=axis, keepdims=True)


def safe_log(x: np.ndarray) -> np.ndarray:
    return np.log(np.asarray(x, dtype=float) + _EPS)


def variational_free_energy(
    qs: np.ndarray,
    qs_prior: np.ndarray,
    log_likelihood: np.ndarray,
) -> float:
    """F[Q] = KL[Q(s) || prior(s)] - E_Q[log P(o | s, a)]

    Minimising F over Q yields Bayesian belief updating; when Q is
    unconstrained, the optimum is Q(s) ∝ prior(s) * P(o|s).
    """
    qs = np.asarray(qs, dtype=float)
    kl = float((qs * (safe_log(qs) - safe_log(qs_prior))).sum())
    accuracy = float((qs * log_likelihood).sum())
    return kl - accuracy


def expected_free_energy(
    qs: np.ndarray,
    A_a: np.ndarray,
    B_a: np.ndarray,
    C: np.ndarray,
) -> tuple[float, float, float]:
    """G(a) = - pragmatic_value - epistemic_value

    Args:
        qs:  current belief over states, shape (n_states,)
        A_a: likelihood under action a, shape (n_obs, n_states)
        B_a: transition under action a, shape (n_states, n_states)
        C:   log preferences over observations, shape (n_obs,)

    Returns:
        (G, pragmatic_value, epistemic_value)
    """
    qs_next = B_a @ qs                       # (n_states,)
    qo = A_a @ qs_next                       # (n_obs,)

    pragmatic = float((qo * C).sum())

    # epistemic = mutual information I(s'; o | a)
    #           = sum_s' Q(s'|a) * KL[ P(o|s', a) || Q(o|a) ]
    log_qo = safe_log(qo)
    log_A = safe_log(A_a)                    # (n_obs, n_states)
    kl_per_state = ((A_a * (log_A - log_qo[:, None])).sum(axis=0))  # (n_states,)
    epistemic = float((qs_next * kl_per_state).sum())

    G = -pragmatic - epistemic
    return G, pragmatic, epistemic


class ActiveInferenceAgent:
    """Discrete-state, discrete-action active inference agent.

    Action-conditioned likelihood A[a, o, s] is supported so the same
    framework handles cases where the same hidden state produces different
    observation distributions depending on the agent's action (e.g. portfolio
    payoffs depend on the chosen position).
    """

    def __init__(
        self,
        A: np.ndarray,
        B: np.ndarray,
        C: np.ndarray,
        D: np.ndarray,
        gamma: float = 4.0,
    ):
        self.A = np.asarray(A, dtype=float)
        self.B = np.asarray(B, dtype=float)
        self.C = np.asarray(C, dtype=float)
        self.D = np.asarray(D, dtype=float)
        self.gamma = float(gamma)

        if self.A.ndim != 3:
            raise ValueError(f"A must be 3D (n_actions, n_obs, n_states); got {self.A.shape}")
        self.n_actions, self.n_obs, self.n_states = self.A.shape
        if self.B.shape != (self.n_actions, self.n_states, self.n_states):
            raise ValueError(f"B must be {(self.n_actions, self.n_states, self.n_states)}; got {self.B.shape}")
        if self.C.shape != (self.n_obs,):
            raise ValueError(f"C must be ({self.n_obs},); got {self.C.shape}")
        if self.D.shape != (self.n_states,):
            raise ValueError(f"D must be ({self.n_states},); got {self.D.shape}")

        self.qs = normalize(self.D)

    def expected_free_energy(self, action: int) -> tuple[float, float, float]:
        return expected_free_energy(self.qs, self.A[action], self.B[action], self.C)

    def policy_distribution(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (action_probabilities, G_per_action). Acts minimize G."""
        G = np.array([self.expected_free_energy(a)[0] for a in range(self.n_actions)])
        return softmax(-self.gamma * G), G

    def update_belief(self, action: int, obs: int) -> np.ndarray:
        """Bayesian belief update:  Q(s') ∝ P(o | s', a) * (B[a] @ Q(s))."""
        predicted = self.B[action] @ self.qs
        likelihood = self.A[action, obs, :]
        self.qs = normalize(likelihood * predicted)
        return self.qs

    def reset(self) -> None:
        self.qs = normalize(self.D)
