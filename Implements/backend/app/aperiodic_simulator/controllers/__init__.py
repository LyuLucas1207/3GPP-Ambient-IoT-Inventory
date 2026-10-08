from app.aperiodic_simulator.controllers.base import Action, Controller
from app.aperiodic_simulator.controllers.cmebe import CMEBEController
from app.aperiodic_simulator.controllers.dfsa_schoute import DFSASchouteController
from app.aperiodic_simulator.controllers.pfsa_pze import PFSAPZEController
from app.aperiodic_simulator.core.states import ControllerName


def make_controller(name: ControllerName | str, F: int, L_max: int, p_floor: float, **kwargs) -> Controller:
    name = ControllerName(name)
    if name == ControllerName.PFSA_PZE:
        return PFSAPZEController(F, L_max, p_floor, idle_floor=kwargs.get("idle_floor", 1.0))
    if name == ControllerName.DFSA_SCHOUTE:
        return DFSASchouteController(F, L_max, p_floor)
    if name == ControllerName.CMEBE:
        return CMEBEController(F, L_max, p_floor)
    if name == ControllerName.RECURRENT_PPO:
        raise ValueError("recurrent_ppo is built from a checkpoint: use controllers.recurrent_ppo.ppo_controller_factory")
    raise ValueError(f"unknown controller {name}")


__all__ = ["Action", "Controller", "CMEBEController", "DFSASchouteController", "PFSAPZEController", "make_controller"]
