"""Table II and Table III of the aperiodic journal paper.

Lives next to the three simulators, not inside one of them. ``aperiodic_simulator``,
``simulator``, and ``thesis_simulator`` read these names and do not import each other.
"""

from __future__ import annotations

# Table II — indoor factory and radio

FACTORY_LENGTH_M = 120.0  # factory length
FACTORY_WIDTH_M = 60.0  # factory width
N_BS = 18  # base stations on the 20 m lattice
BS_SPACING_M = 20.0  # spacing between base stations
BS_HEIGHT_M = 8.0  # base-station antenna height
DEVICE_HEIGHT_M = 1.5  # device antenna height
CARRIER_GHZ = 0.9  # carrier frequency
POLARIZATION_LOSS_DB = 3.0  # polarization mismatch loss
SHADOW_FADING_MARGIN_DB = 4.0  # shadow fading margin
ON_OBJECT_PENALTY_DB = 0.9  # extra loss when the device sits on an object
BS_RX_SENSITIVITY_DBM = -106.0  # base-station receive sensitivity
BS_TX_POWER_DBM = 33.0  # base-station transmit power
BS_TX_ANTENNA_GAIN_DBI = 6.0  # base-station transmit antenna gain
F = 8  # frequency resources in one round
DATA_RATE_BPS = 7000.0  # line rate
PAGING_BITS = 80  # paging message length
MSG1_BITS = 38  # Msg1 length
MSG2_BITS = 88  # Msg2 length
MSG3_BITS = 144  # Msg3 length
EI_OVERHEAD_BITS = 24  # energy-indicator overhead
FALSE_ALARM_RATE = 0.001  # idle resource declared occupied
MISSED_DETECTION_RATE = 0.01  # occupied resource declared idle
CAPTURE_RATIO_DB = 6.0  # strongest signal must exceed the sum of the others by this
T_MON_S = 0.100  # pre-page monitoring time
P_SL_W = 0.1e-6  # sleep power
P_WURX_W = 1.0e-6  # wake-up receiver power
SINGLE_SOURCE_MIN_PIN_DBM = -36.0  # devices below this incident power are left out of the single-source scene
N_TOT_MIN = 100  # smallest device count drawn while training
N_TOT_MAX = 15000  # largest device count in the paper, and the default episode size

# Table II — device type 1 (backscatter)

TYPE1_RX_SENSITIVITY_DBM = -36.0  # type 1 receive sensitivity
TYPE1_P_TX_W = 1e-6  # type 1 transmit power
TYPE1_P_RX_W = 1e-6  # type 1 receive power; it also monitors with this receiver
TYPE1_E_UP_J = 5e-6  # type 1 energy to wake
TYPE1_E_LOW_J = 2.5e-6  # type 1 energy floor before it turns off
TYPE1_BACKSCATTER_LOSS_DB = 6.0  # type 1 backscatter loss

# Table II — device type 2a (backscatter, wake-up receiver)

TYPE2A_RX_SENSITIVITY_DBM = -40.0  # type 2a receive sensitivity
TYPE2A_P_TX_W = 200e-6  # type 2a transmit power
TYPE2A_P_RX_W = 50e-6  # type 2a receive power
TYPE2A_E_UP_J = 25e-6  # type 2a energy to wake
TYPE2A_E_LOW_J = 12.5e-6  # type 2a energy floor before it turns off
TYPE2A_BACKSCATTER_LOSS_DB = 6.0  # type 2a backscatter loss
TYPE2A_BACKSCATTER_GAIN_DB = 10.0  # type 2a backscatter antenna gain

# Table II — device type 2b (active uplink, wake-up receiver)

TYPE2B_RX_SENSITIVITY_DBM = -70.0  # type 2b receive sensitivity
TYPE2B_P_TX_W = 200e-6  # type 2b transmit power
TYPE2B_P_RX_W = 50e-6  # type 2b receive power
TYPE2B_E_UP_J = 25e-6  # type 2b energy to wake
TYPE2B_E_LOW_J = 12.5e-6  # type 2b energy floor before it turns off
TYPE2B_ACTIVE_TX_POWER_DBM = -20.0  # type 2b active transmit power

# Table III — Recurrent PPO

LEARNING_RATE = 3e-4  # Adam step size
GAMMA = 0.9  # discount
GAE_LAMBDA = 0.95  # GAE smoothing
CLIP_RANGE = 0.2  # PPO clip
ENT_COEF = 0.01  # entropy bonus weight
VF_COEF = 0.02  # value-loss weight
MAX_GRAD_NORM = 0.5  # gradient clip
N_STEPS = 2048  # steps collected before one update
BATCH_SIZE = 256  # minibatch size
N_EPOCHS = 10  # passes over one rollout
TOTAL_TIMESTEPS = 1_000_000  # training length in the paper
ALPHA = 0.5  # reward weight on collisions against new identifications
M_MIN = 0.25  # smallest multiplier of the previous frame length
M_MAX = 10.0  # largest multiplier of the previous frame length
Q_MIN = 0.1  # smallest multiplier of the previous access probability
Q_MAX = 10.0  # largest multiplier of the previous access probability
LSTM_HIDDEN = 128  # LSTM width
N_LSTM_LAYERS = 1  # LSTM depth
MLP_WIDTH = 128  # width of each of the two layers after the LSTM
L_MAX = 83  # longest frame, in time slots
L_INITIAL = (1, 2, 4, 8, 16, 32)  # frame length drawn for the first round of a training episode

PYTHON_PATH = "Implements/backend/app/journal/tables.py"  # this file
FRONTEND_PATH = "Implements/frontend/src/constants/journalTables.ts"  # the same numbers for the page


def _row(name: str, value, unit: str = "") -> dict:
    return {"name": name, "value": value if isinstance(value, (int, float, str)) else list(value), "unit": unit}


def table_ii_rows() -> list[dict]:
    return [
        _row("FACTORY_LENGTH_M", FACTORY_LENGTH_M, "m"),
        _row("FACTORY_WIDTH_M", FACTORY_WIDTH_M, "m"),
        _row("N_BS", N_BS, ""),
        _row("BS_SPACING_M", BS_SPACING_M, "m"),
        _row("BS_HEIGHT_M", BS_HEIGHT_M, "m"),
        _row("DEVICE_HEIGHT_M", DEVICE_HEIGHT_M, "m"),
        _row("CARRIER_GHZ", CARRIER_GHZ, "GHz"),
        _row("POLARIZATION_LOSS_DB", POLARIZATION_LOSS_DB, "dB"),
        _row("SHADOW_FADING_MARGIN_DB", SHADOW_FADING_MARGIN_DB, "dB"),
        _row("ON_OBJECT_PENALTY_DB", ON_OBJECT_PENALTY_DB, "dB"),
        _row("BS_RX_SENSITIVITY_DBM", BS_RX_SENSITIVITY_DBM, "dBm"),
        _row("BS_TX_POWER_DBM", BS_TX_POWER_DBM, "dBm"),
        _row("BS_TX_ANTENNA_GAIN_DBI", BS_TX_ANTENNA_GAIN_DBI, "dBi"),
        _row("F", F, ""),
        _row("DATA_RATE_BPS", DATA_RATE_BPS, "bit/s"),
        _row("PAGING_BITS", PAGING_BITS, "bit"),
        _row("MSG1_BITS", MSG1_BITS, "bit"),
        _row("MSG2_BITS", MSG2_BITS, "bit"),
        _row("MSG3_BITS", MSG3_BITS, "bit"),
        _row("EI_OVERHEAD_BITS", EI_OVERHEAD_BITS, "bit"),
        _row("FALSE_ALARM_RATE", FALSE_ALARM_RATE, ""),
        _row("MISSED_DETECTION_RATE", MISSED_DETECTION_RATE, ""),
        _row("CAPTURE_RATIO_DB", CAPTURE_RATIO_DB, "dB"),
        _row("T_MON_S", T_MON_S, "s"),
        _row("P_SL_W", P_SL_W, "W"),
        _row("P_WURX_W", P_WURX_W, "W"),
        _row("SINGLE_SOURCE_MIN_PIN_DBM", SINGLE_SOURCE_MIN_PIN_DBM, "dBm"),
        _row("N_TOT_MIN", N_TOT_MIN, ""),
        _row("N_TOT_MAX", N_TOT_MAX, ""),
        _row("TYPE1_RX_SENSITIVITY_DBM", TYPE1_RX_SENSITIVITY_DBM, "dBm"),
        _row("TYPE1_P_TX_W", TYPE1_P_TX_W, "W"),
        _row("TYPE1_P_RX_W", TYPE1_P_RX_W, "W"),
        _row("TYPE1_E_UP_J", TYPE1_E_UP_J, "J"),
        _row("TYPE1_E_LOW_J", TYPE1_E_LOW_J, "J"),
        _row("TYPE1_BACKSCATTER_LOSS_DB", TYPE1_BACKSCATTER_LOSS_DB, "dB"),
        _row("TYPE2A_RX_SENSITIVITY_DBM", TYPE2A_RX_SENSITIVITY_DBM, "dBm"),
        _row("TYPE2A_P_TX_W", TYPE2A_P_TX_W, "W"),
        _row("TYPE2A_P_RX_W", TYPE2A_P_RX_W, "W"),
        _row("TYPE2A_E_UP_J", TYPE2A_E_UP_J, "J"),
        _row("TYPE2A_E_LOW_J", TYPE2A_E_LOW_J, "J"),
        _row("TYPE2A_BACKSCATTER_LOSS_DB", TYPE2A_BACKSCATTER_LOSS_DB, "dB"),
        _row("TYPE2A_BACKSCATTER_GAIN_DB", TYPE2A_BACKSCATTER_GAIN_DB, "dB"),
        _row("TYPE2B_RX_SENSITIVITY_DBM", TYPE2B_RX_SENSITIVITY_DBM, "dBm"),
        _row("TYPE2B_P_TX_W", TYPE2B_P_TX_W, "W"),
        _row("TYPE2B_P_RX_W", TYPE2B_P_RX_W, "W"),
        _row("TYPE2B_E_UP_J", TYPE2B_E_UP_J, "J"),
        _row("TYPE2B_E_LOW_J", TYPE2B_E_LOW_J, "J"),
        _row("TYPE2B_ACTIVE_TX_POWER_DBM", TYPE2B_ACTIVE_TX_POWER_DBM, "dBm"),
    ]


def table_iii_rows() -> list[dict]:
    return [
        _row("LEARNING_RATE", LEARNING_RATE, ""),
        _row("GAMMA", GAMMA, ""),
        _row("GAE_LAMBDA", GAE_LAMBDA, ""),
        _row("CLIP_RANGE", CLIP_RANGE, ""),
        _row("ENT_COEF", ENT_COEF, ""),
        _row("VF_COEF", VF_COEF, ""),
        _row("MAX_GRAD_NORM", MAX_GRAD_NORM, ""),
        _row("N_STEPS", N_STEPS, ""),
        _row("BATCH_SIZE", BATCH_SIZE, ""),
        _row("N_EPOCHS", N_EPOCHS, ""),
        _row("TOTAL_TIMESTEPS", TOTAL_TIMESTEPS, ""),
        _row("ALPHA", ALPHA, ""),
        _row("M_MIN", M_MIN, ""),
        _row("M_MAX", M_MAX, ""),
        _row("Q_MIN", Q_MIN, ""),
        _row("Q_MAX", Q_MAX, ""),
        _row("LSTM_HIDDEN", LSTM_HIDDEN, ""),
        _row("N_LSTM_LAYERS", N_LSTM_LAYERS, ""),
        _row("MLP_WIDTH", MLP_WIDTH, ""),
        _row("L_MAX", L_MAX, "time slots"),
        _row("L_INITIAL", L_INITIAL, ""),
    ]


def journal_payload() -> dict:
    return {
        "table_ii": table_ii_rows(),
        "table_iii": table_iii_rows(),
        "python_path": PYTHON_PATH,
        "frontend_path": FRONTEND_PATH,
    }
