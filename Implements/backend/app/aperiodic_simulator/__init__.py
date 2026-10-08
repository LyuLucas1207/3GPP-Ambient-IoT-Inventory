"""Scientific engine for "3GPP Ambient IoT Inventory with Aperiodic Paging" (Kota et al.).

This package is independent of the legacy ``app.simulator`` package. It shares only the
pure utilities in ``app.common`` (RF conversion and inventory-curve metrics).

Subpackages: ``core`` (config, states, timing, simulation loop, runners), ``physics``
(layout, channel, harvesting, energy, impairments), ``protocol`` (paging, CBRA, grouping),
``controllers`` (PFSA-PZE, DFSA-Schoute, CMEBE, recurrent PPO), ``rl`` (training/checkpoints),
``analysis`` (metrics, paper reference data), ``reproduction`` (paper figures/tables) and
``runtime`` (API service, background jobs, run store).
"""
