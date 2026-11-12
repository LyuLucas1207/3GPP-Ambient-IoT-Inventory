"""Training algorithms. Each module exposes ``train(job, out_dir, log) -> artifact dict``.

* ``ps_ppo``      - stable-baselines3 PPO, one MLP shared by every reader.
* ``mappo``       - torch PPO with a centralized critic (CTDE) and a shared actor.
* ``independent`` - IPPO baseline: one actor and one local critic per reader slot.
* ``zero_shot``   - no training: the single-reader RecurrentPPO on every reader.
"""
