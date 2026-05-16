"""Toy active-inference demo: regime detection + portfolio choice.

Hidden state s ∈ {Bull, Bear} switches stochastically over time. The agent
sees only its own portfolio outcome (Gain / Flat / Loss), which depends
jointly on the regime and the action it just took. Aggressive / Defensive
positions are simultaneously informative (high signal-to-noise) and risky,
while Hold is uninformative but safe — exactly the explore/exploit tension
that Expected Free Energy is meant to balance.

Run:  python -m agi_math.financial_demo
"""

from __future__ import annotations

import numpy as np

from .core import ActiveInferenceAgent


STATE_NAMES = ["Bull", "Bear"]
ACTION_NAMES = ["Aggressive", "Hold", "Defensive"]
OBS_NAMES = ["Gain", "Flat", "Loss"]
PNL_BY_OBS = {0: +1.0, 1: 0.0, 2: -1.0}


def build_market_model():
    # A[a, o, s] = P(o | s, a)
    A = np.zeros((3, 3, 2))
    A[0, :, 0] = [0.75, 0.15, 0.10]   # Aggressive | Bull → mostly Gain
    A[0, :, 1] = [0.10, 0.15, 0.75]   # Aggressive | Bear → mostly Loss
    A[1, :, 0] = [0.30, 0.55, 0.15]   # Hold       | Bull → mostly Flat, small Gain skew
    A[1, :, 1] = [0.15, 0.55, 0.30]   # Hold       | Bear → mostly Flat, small Loss skew
    A[2, :, 0] = [0.10, 0.30, 0.60]   # Defensive  | Bull → counter-trend hurts
    A[2, :, 1] = [0.60, 0.30, 0.10]   # Defensive  | Bear → shorting profits

    # Regimes are sticky and not influenced by the agent's actions.
    transition = np.array([[0.92, 0.08],
                           [0.08, 0.92]])
    B = np.tile(transition, (3, 1, 1))

    C = np.array([2.0, 0.0, -2.0])    # log preferences: love Gain, hate Loss
    D = np.array([0.5, 0.5])          # uniform prior over regime
    return A, B, C, D


def simulate(T: int = 30, regime_switch_at: int | None = None, seed: int = 0):
    rng = np.random.default_rng(seed)
    A, B, C, D = build_market_model()
    agent = ActiveInferenceAgent(A, B, C, D, gamma=4.0)

    if regime_switch_at is None:
        regime_switch_at = T // 2
    true_states = np.zeros(T, dtype=int)
    true_states[regime_switch_at:] = 1

    history = []
    pnl = 0.0
    for t in range(T):
        s_true = int(true_states[t])
        pi, G = agent.policy_distribution()
        a = int(rng.choice(3, p=pi))
        o = int(rng.choice(3, p=A[a, :, s_true]))
        agent.update_belief(a, o)

        pnl += PNL_BY_OBS[o]
        history.append({
            "t": t,
            "true_state": STATE_NAMES[s_true],
            "p_bull": float(agent.qs[0]),
            "action": ACTION_NAMES[a],
            "obs": OBS_NAMES[o],
            "G": G.tolist(),
            "pnl": pnl,
        })
    return history


def _print_run(history):
    header = f"{'t':>3} {'regime':>6} {'P(Bull)':>8} {'action':>11} {'outcome':>7} {'cum PnL':>8}"
    print(header)
    print("-" * len(header))
    for row in history:
        print(
            f"{row['t']:>3} {row['true_state']:>6} {row['p_bull']:>8.3f} "
            f"{row['action']:>11} {row['obs']:>7} {row['pnl']:>8.2f}"
        )


if __name__ == "__main__":
    h = simulate(T=30, regime_switch_at=15, seed=7)
    _print_run(h)
    final = h[-1]
    print()
    print(f"Final belief P(Bull) = {final['p_bull']:.3f} (true regime: {final['true_state']})")
    print(f"Cumulative PnL = {final['pnl']:+.2f}")
