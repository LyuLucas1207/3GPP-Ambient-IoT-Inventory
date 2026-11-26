/** Table II and Table III. Same numbers as `Implements/backend/app/journal/tables.py`. */

export type JournalRow = { name: string; value: number | number[]; unit: string }

export const JOURNAL_PYTHON_PATH = 'Implements/backend/app/journal/tables.py' // backend file the simulators import
export const JOURNAL_FRONTEND_PATH = 'Implements/frontend/src/constants/journalTables.ts' // this file

export const FACTORY_LENGTH_M = 120 // factory length, m
export const FACTORY_WIDTH_M = 60 // factory width, m
export const N_BS = 18 // base stations on the lattice
export const BS_SPACING_M = 20 // spacing between base stations, m
export const BS_HEIGHT_M = 8 // base-station antenna height, m
export const DEVICE_HEIGHT_M = 1.5 // device antenna height, m
export const CARRIER_GHZ = 0.9 // carrier frequency, GHz
export const POLARIZATION_LOSS_DB = 3 // polarization mismatch loss, dB
export const SHADOW_FADING_MARGIN_DB = 4 // shadow fading margin, dB
export const ON_OBJECT_PENALTY_DB = 0.9 // extra loss when the device sits on an object, dB
export const BS_RX_SENSITIVITY_DBM = -106 // base-station receive sensitivity, dBm
export const BS_TX_POWER_DBM = 33 // base-station transmit power, dBm
export const BS_TX_ANTENNA_GAIN_DBI = 6 // base-station transmit antenna gain, dBi
export const F = 8 // frequency resources in one round
export const DATA_RATE_BPS = 7000 // line rate, bit/s
export const PAGING_BITS = 80 // paging message length, bit
export const MSG1_BITS = 38 // Msg1 length, bit
export const MSG2_BITS = 88 // Msg2 length, bit
export const MSG3_BITS = 144 // Msg3 length, bit
export const EI_OVERHEAD_BITS = 24 // energy-indicator overhead, bit
export const FALSE_ALARM_RATE = 0.001 // idle resource declared occupied
export const MISSED_DETECTION_RATE = 0.01 // occupied resource declared idle
export const CAPTURE_RATIO_DB = 6 // strongest signal over the sum of the others, dB
export const T_MON_S = 0.1 // pre-page monitoring time, s
export const P_SL_W = 1e-7 // sleep power, W
export const P_WURX_W = 1e-6 // wake-up receiver power, W
export const SINGLE_SOURCE_MIN_PIN_DBM = -36 // single-source incident-power floor, dBm
export const N_TOT_MIN = 100 // smallest device count drawn while training
export const N_TOT_MAX = 15000 // largest device count, and the default episode size

export const TYPE1_RX_SENSITIVITY_DBM = -36 // type 1 receive sensitivity, dBm
export const TYPE1_P_TX_W = 1e-6 // type 1 transmit power, W
export const TYPE1_P_RX_W = 1e-6 // type 1 receive power, W
export const TYPE1_E_UP_J = 5e-6 // type 1 energy to wake, J
export const TYPE1_E_LOW_J = 2.5e-6 // type 1 energy floor, J
export const TYPE1_BACKSCATTER_LOSS_DB = 6 // type 1 backscatter loss, dB

export const TYPE2A_RX_SENSITIVITY_DBM = -40 // type 2a receive sensitivity, dBm
export const TYPE2A_P_TX_W = 200e-6 // type 2a transmit power, W
export const TYPE2A_P_RX_W = 50e-6 // type 2a receive power, W
export const TYPE2A_E_UP_J = 25e-6 // type 2a energy to wake, J
export const TYPE2A_E_LOW_J = 12.5e-6 // type 2a energy floor, J
export const TYPE2A_BACKSCATTER_LOSS_DB = 6 // type 2a backscatter loss, dB
export const TYPE2A_BACKSCATTER_GAIN_DB = 10 // type 2a backscatter antenna gain, dB

export const TYPE2B_RX_SENSITIVITY_DBM = -70 // type 2b receive sensitivity, dBm
export const TYPE2B_P_TX_W = 200e-6 // type 2b transmit power, W
export const TYPE2B_P_RX_W = 50e-6 // type 2b receive power, W
export const TYPE2B_E_UP_J = 25e-6 // type 2b energy to wake, J
export const TYPE2B_E_LOW_J = 12.5e-6 // type 2b energy floor, J
export const TYPE2B_ACTIVE_TX_POWER_DBM = -20 // type 2b active transmit power, dBm

export const LEARNING_RATE = 0.0003 // Adam step size
export const GAMMA = 0.9 // discount
export const GAE_LAMBDA = 0.95 // GAE smoothing
export const CLIP_RANGE = 0.2 // PPO clip
export const ENT_COEF = 0.01 // entropy bonus weight
export const VF_COEF = 0.02 // value-loss weight
export const MAX_GRAD_NORM = 0.5 // gradient clip
export const N_STEPS = 2048 // steps collected before one update
export const BATCH_SIZE = 256 // minibatch size
export const N_EPOCHS = 10 // passes over one rollout
export const TOTAL_TIMESTEPS = 1_000_000 // training length in the paper
export const ALPHA = 0.5 // reward weight on collisions against new identifications
export const M_MIN = 0.25 // smallest multiplier of the previous frame length
export const M_MAX = 10 // largest multiplier of the previous frame length
export const Q_MIN = 0.1 // smallest multiplier of the previous access probability
export const Q_MAX = 10 // largest multiplier of the previous access probability
export const LSTM_HIDDEN = 128 // LSTM width
export const N_LSTM_LAYERS = 1 // LSTM depth
export const MLP_WIDTH = 128 // width of each of the two layers after the LSTM
export const L_MAX = 83 // longest frame, in time slots
export const L_INITIAL = [1, 2, 4, 8, 16, 32] // frame length drawn for the first training round

export const TABLE_II: JournalRow[] = [
  { name: 'FACTORY_LENGTH_M', value: FACTORY_LENGTH_M, unit: 'm' },
  { name: 'FACTORY_WIDTH_M', value: FACTORY_WIDTH_M, unit: 'm' },
  { name: 'N_BS', value: N_BS, unit: '' },
  { name: 'BS_SPACING_M', value: BS_SPACING_M, unit: 'm' },
  { name: 'BS_HEIGHT_M', value: BS_HEIGHT_M, unit: 'm' },
  { name: 'DEVICE_HEIGHT_M', value: DEVICE_HEIGHT_M, unit: 'm' },
  { name: 'CARRIER_GHZ', value: CARRIER_GHZ, unit: 'GHz' },
  { name: 'POLARIZATION_LOSS_DB', value: POLARIZATION_LOSS_DB, unit: 'dB' },
  { name: 'SHADOW_FADING_MARGIN_DB', value: SHADOW_FADING_MARGIN_DB, unit: 'dB' },
  { name: 'ON_OBJECT_PENALTY_DB', value: ON_OBJECT_PENALTY_DB, unit: 'dB' },
  { name: 'BS_RX_SENSITIVITY_DBM', value: BS_RX_SENSITIVITY_DBM, unit: 'dBm' },
  { name: 'BS_TX_POWER_DBM', value: BS_TX_POWER_DBM, unit: 'dBm' },
  { name: 'BS_TX_ANTENNA_GAIN_DBI', value: BS_TX_ANTENNA_GAIN_DBI, unit: 'dBi' },
  { name: 'F', value: F, unit: '' },
  { name: 'DATA_RATE_BPS', value: DATA_RATE_BPS, unit: 'bit/s' },
  { name: 'PAGING_BITS', value: PAGING_BITS, unit: 'bit' },
  { name: 'MSG1_BITS', value: MSG1_BITS, unit: 'bit' },
  { name: 'MSG2_BITS', value: MSG2_BITS, unit: 'bit' },
  { name: 'MSG3_BITS', value: MSG3_BITS, unit: 'bit' },
  { name: 'EI_OVERHEAD_BITS', value: EI_OVERHEAD_BITS, unit: 'bit' },
  { name: 'FALSE_ALARM_RATE', value: FALSE_ALARM_RATE, unit: '' },
  { name: 'MISSED_DETECTION_RATE', value: MISSED_DETECTION_RATE, unit: '' },
  { name: 'CAPTURE_RATIO_DB', value: CAPTURE_RATIO_DB, unit: 'dB' },
  { name: 'T_MON_S', value: T_MON_S, unit: 's' },
  { name: 'P_SL_W', value: P_SL_W, unit: 'W' },
  { name: 'P_WURX_W', value: P_WURX_W, unit: 'W' },
  { name: 'SINGLE_SOURCE_MIN_PIN_DBM', value: SINGLE_SOURCE_MIN_PIN_DBM, unit: 'dBm' },
  { name: 'N_TOT_MIN', value: N_TOT_MIN, unit: '' },
  { name: 'N_TOT_MAX', value: N_TOT_MAX, unit: '' },
  { name: 'TYPE1_RX_SENSITIVITY_DBM', value: TYPE1_RX_SENSITIVITY_DBM, unit: 'dBm' },
  { name: 'TYPE1_P_TX_W', value: TYPE1_P_TX_W, unit: 'W' },
  { name: 'TYPE1_P_RX_W', value: TYPE1_P_RX_W, unit: 'W' },
  { name: 'TYPE1_E_UP_J', value: TYPE1_E_UP_J, unit: 'J' },
  { name: 'TYPE1_E_LOW_J', value: TYPE1_E_LOW_J, unit: 'J' },
  { name: 'TYPE1_BACKSCATTER_LOSS_DB', value: TYPE1_BACKSCATTER_LOSS_DB, unit: 'dB' },
  { name: 'TYPE2A_RX_SENSITIVITY_DBM', value: TYPE2A_RX_SENSITIVITY_DBM, unit: 'dBm' },
  { name: 'TYPE2A_P_TX_W', value: TYPE2A_P_TX_W, unit: 'W' },
  { name: 'TYPE2A_P_RX_W', value: TYPE2A_P_RX_W, unit: 'W' },
  { name: 'TYPE2A_E_UP_J', value: TYPE2A_E_UP_J, unit: 'J' },
  { name: 'TYPE2A_E_LOW_J', value: TYPE2A_E_LOW_J, unit: 'J' },
  { name: 'TYPE2A_BACKSCATTER_LOSS_DB', value: TYPE2A_BACKSCATTER_LOSS_DB, unit: 'dB' },
  { name: 'TYPE2A_BACKSCATTER_GAIN_DB', value: TYPE2A_BACKSCATTER_GAIN_DB, unit: 'dB' },
  { name: 'TYPE2B_RX_SENSITIVITY_DBM', value: TYPE2B_RX_SENSITIVITY_DBM, unit: 'dBm' },
  { name: 'TYPE2B_P_TX_W', value: TYPE2B_P_TX_W, unit: 'W' },
  { name: 'TYPE2B_P_RX_W', value: TYPE2B_P_RX_W, unit: 'W' },
  { name: 'TYPE2B_E_UP_J', value: TYPE2B_E_UP_J, unit: 'J' },
  { name: 'TYPE2B_E_LOW_J', value: TYPE2B_E_LOW_J, unit: 'J' },
  { name: 'TYPE2B_ACTIVE_TX_POWER_DBM', value: TYPE2B_ACTIVE_TX_POWER_DBM, unit: 'dBm' },
]

export const TABLE_III: JournalRow[] = [
  { name: 'LEARNING_RATE', value: LEARNING_RATE, unit: '' },
  { name: 'GAMMA', value: GAMMA, unit: '' },
  { name: 'GAE_LAMBDA', value: GAE_LAMBDA, unit: '' },
  { name: 'CLIP_RANGE', value: CLIP_RANGE, unit: '' },
  { name: 'ENT_COEF', value: ENT_COEF, unit: '' },
  { name: 'VF_COEF', value: VF_COEF, unit: '' },
  { name: 'MAX_GRAD_NORM', value: MAX_GRAD_NORM, unit: '' },
  { name: 'N_STEPS', value: N_STEPS, unit: '' },
  { name: 'BATCH_SIZE', value: BATCH_SIZE, unit: '' },
  { name: 'N_EPOCHS', value: N_EPOCHS, unit: '' },
  { name: 'TOTAL_TIMESTEPS', value: TOTAL_TIMESTEPS, unit: '' },
  { name: 'ALPHA', value: ALPHA, unit: '' },
  { name: 'M_MIN', value: M_MIN, unit: '' },
  { name: 'M_MAX', value: M_MAX, unit: '' },
  { name: 'Q_MIN', value: Q_MIN, unit: '' },
  { name: 'Q_MAX', value: Q_MAX, unit: '' },
  { name: 'LSTM_HIDDEN', value: LSTM_HIDDEN, unit: '' },
  { name: 'N_LSTM_LAYERS', value: N_LSTM_LAYERS, unit: '' },
  { name: 'MLP_WIDTH', value: MLP_WIDTH, unit: '' },
  { name: 'L_MAX', value: L_MAX, unit: 'time slots' },
  { name: 'L_INITIAL', value: L_INITIAL, unit: '' },
]

export function formatJournalValue(value: number | number[]): string {
  if (Array.isArray(value)) return value.join(', ')
  if (value !== 0 && Math.abs(value) < 1e-3) return value.toExponential(0)
  return String(value)
}
