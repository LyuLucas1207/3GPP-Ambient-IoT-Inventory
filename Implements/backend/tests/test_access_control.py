from simulator.access_control import AccessProbabilityController


def test_idle_with_no_eligible_does_not_raise_p():
    ctrl = AccessProbabilityController(n_ao=8, n_devices=150, p_init=0.064)
    p0 = ctrl.p
    assert ctrl.observe(8, n_eligible=0, n_transmitted=0) == p0


def test_energy_limited_transmissions_do_not_raise_p():
    ctrl = AccessProbabilityController(n_ao=8, n_devices=150, p_init=0.064)
    p0 = ctrl.p
    # 2 Msg1 TX, 6 idle AOs looks like "p too small" but is harvesting.
    p1 = ctrl.observe(6, n_eligible=25, n_transmitted=2)
    assert p1 == p0


def test_ungated_mode_raises_p_on_energy_limited_idle():
    ungated = AccessProbabilityController(
        n_ao=8, n_devices=150, p_init=0.064, mode="poisson_idle_ungated"
    )
    p0 = ungated.p
    p1 = ungated.observe(6, n_eligible=25, n_transmitted=2)
    assert p1 != p0


def test_fixed_mode_never_updates():
    ctrl = AccessProbabilityController(n_ao=8, n_devices=150, p_init=0.064, mode="fixed")
    assert ctrl.observe(0, n_eligible=120, n_transmitted=10) == 0.064
