"""Inventory simulation engine (FSA + DCM + multi-reader), stepped frame by frame.

``episode`` builds/steps/finishes an episode, ``checkpoint`` serializes it for
pause/resume, and ``live`` runs it on a background thread with real-time
pacing and fan-out to SSE subscribers.
"""
