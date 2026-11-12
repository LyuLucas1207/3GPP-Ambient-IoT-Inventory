"""Multi-reader reinforcement learning for the thesis engine.

* ``features``  - observation / action transforms (shared by training and runs)
* ``env``       - ``MultiReaderInventoryEnv`` (Gymnasium, one step = one reader frame)
* ``policy``    - policy registry and ``PolicyController`` for live runs

Training code lives outside the app, in ``Implements/backend/training/``.
"""
