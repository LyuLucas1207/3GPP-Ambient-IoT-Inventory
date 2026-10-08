#!/usr/bin/env python3
"""Train the Recurrent PPO controller of the aperiodic-paging paper (Table III).

    python backend/scripts/aperiodic/train_ppo/train_ppo.py --steps 1000000 --seed 42 [--alpha 0.5]

Writes aperiodic_simulator/rl/checkpoints/recurrent_ppo_alpha_<a>.zip and a
.json metadata sidecar (steps, seed, config hash, versions, git commit,
SHA-256, transforms). Optionally evaluates the result on the Figure 7 setting.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.aperiodic_simulator.rl.train import PAPER_TRAINING_STEPS, train


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", type=int, default=PAPER_TRAINING_STEPS, help="total environment steps (CBRA rounds)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--alpha", type=float, default=0.5, help="reward weight alpha of Eq. (8)")
    ap.add_argument("--eval-episodes", type=int, default=0, help="evaluate on N_tot=15000 multi-source, L1=1 after training")
    args = ap.parse_args()

    meta = train(args.steps, args.seed, args.alpha)
    if meta["training_steps"] < PAPER_TRAINING_STEPS:
        print(f"note: {meta['training_steps']} steps < paper's {PAPER_TRAINING_STEPS}; results are not the paper's trained policy")
    if args.eval_episodes > 0:
        from app.aperiodic_simulator.rl.evaluate import evaluate_ppo

        br = evaluate_ppo(args.alpha, episodes=args.eval_episodes)
        a = br.aggregate
        fmt = lambda k: "n/a" if not a.get(k) else f"{a[k]['mean']:.1f}"
        print(
            f"eval multi-source N=15000 L1=1, {args.eval_episodes} episodes: "
            f"mean ID time {fmt('mean_identification_time_s')} s, T99 {fmt('T99')} s, RE {fmt('resource_efficiency')}"
        )


if __name__ == "__main__":
    main()
