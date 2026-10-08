#!/usr/bin/env bash
# Interactive launcher: paper folder -> target folder -> script -> options.
# Enter accepts the [default]; q goes back one level (quits at the top).
# Outputs land next to each script; logs go to <target>/logs/.
#   ./menu.sh                      start at the top
#   ./menu.sh aperiodic figure7    start inside scripts/aperiodic/figure7
set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPTS/.." || exit 1

if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY=python3; fi
NPROC="$(nproc 2>/dev/null || echo 4)"

B=$'\e[1m'; D=$'\e[2m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; C=$'\e[36m'; N=$'\e[0m'
BACK=1

# ---------------------------------------------------------------- prompts

ask() {  # ask VAR "prompt" default -> returns BACK on q
    local __ans
    read -r -p "  $2 [${3}]: " __ans || return $BACK
    [[ "$__ans" == q ]] && return $BACK
    printf -v "$1" '%s' "${__ans:-$3}"
}

yesno() {  # yesno "prompt" y|n -> 0 yes, 1 no, 2 q
    local ans def="${2:-n}"
    read -r -p "  $1 [${def}]: " ans || return 2
    [[ "$ans" == q ]] && return 2
    [[ "${ans:-$def}" =~ ^[yY] ]]
}

ARGS=""
opt() {  # opt --flag "prompt" default ; empty answer and empty default add nothing
    local v
    ask v "$2" "$3" || return $BACK
    [[ -n "$v" ]] && ARGS+=" $1 $v"
    return 0
}
flag() {  # flag --flag "prompt" [default n]
    yesno "$2" "${3:-n}"
    case $? in 0) ARGS+=" $1" ;; 2) return $BACK ;; esac
    return 0
}
confirm() {
    yesno "${Y}$1${N}" n
}

# ---------------------------------------------------------------- per-script options

params() {  # params <paper>/<target>/<script.py> ; sets ARGS, returns BACK on q
    ARGS=""
    case "$1" in
        aperiodic/figure4/reproduce_fig4.py)
            opt --seed "seed" 0 && opt --n-tot "N_tot" 15000 ;;
        aperiodic/figure5/reproduce_fig5.py | aperiodic/figure6/reproduce_fig6.py)
            opt --episodes "episodes per curve (paper 100)" 100 &&
                opt --base-seed "base seed" 0 &&
                opt --workers "workers" "$NPROC" &&
                opt --n-tot "N_tot" 15000 &&
                opt --panels "panels, empty = all (a_L16 b_L1)" "" &&
                flag --no-plot "skip PNG plot?" ;;
        aperiodic/figure7/reproduce_fig7.py | aperiodic/figure8/reproduce_fig8.py | aperiodic/tables/reproduce_tables.py)
            opt --episodes "episodes per method/point (paper 100)" 100 &&
                opt --base-seed "base seed" 0 &&
                opt --workers "workers" "$NPROC" &&
                flag --no-plot "skip PNG plot?" &&
                flag --force "overwrite a cached result that used more episodes?" ;;
        aperiodic/train_ppo/train_ppo.py)
            opt --alpha "alpha (0 / 0.25 / 0.5 / 0.75)" 0.5 &&
                opt --steps "training steps (paper 1000000)" 1000000 &&
                opt --seed "seed" 42 &&
                opt --eval-episodes "evaluation episodes after training (0 = none)" 0 ;;
        aperiodic/validation/validate.py)
            flag --json-only "JSON only (no console table)?" ;;
        aperiodic/digitize/digitize_figures.py)
            confirm "overwrite every aperiodic figure*/paper/*.csv? (needs mutool)" || return $BACK ;;
        periodic/fig5b/digitize_fig5b.py)
            confirm "overwrite periodic/fig5b/paper/*.csv?" || return $BACK ;;
        periodic/fig5b/validate_fig5b.py)
            flag --quick "quick (small N)?" &&
                opt --seed "seed" 42 &&
                opt --monte-carlo "Monte-Carlo seeds (0 = single run)" 0 ;;
        periodic/fig5b/diagnose_fig5b_tail.py)
            flag --quick "quick (N=80, 4 s)?" && opt --seed "seed" 42 ;;
        periodic/assumptions/compare_assumptions.py)
            local scale
            ask scale "scale: quick / paper" quick || return $BACK
            ARGS+=" --$scale"
            opt --which "which: grouping / init / access / dcm_on / all" all ;;
        periodic/assumptions/access_sensitivity.py)
            flag --paper "paper scale (N=600, 25 s, slow)?" ;;
        periodic/fig5a/reproduce_fig5a.py | periodic/fig5b/reproduce_fig5b.py)
            ;;
        *)
            echo "  ${D}no option table for this script; see: $PY scripts/$1 --help${N}"
            local extra
            ask extra "extra arguments" "" || return $BACK
            ARGS=" $extra" ;;
    esac
}

# ---------------------------------------------------------------- running

run_job() {  # run_job <label> <target dir> <command string>
    local label=$1 dir=$2 cmd=$3 mode log
    log="$dir/logs/${label}_$(date +%Y%m%d-%H%M%S).log"
    echo
    echo "  ${C}\$ $cmd${N}"
    echo "  ${D}outputs: $dir/   log: $log${N}"
    ask mode "f = foreground, b = background (nohup)" f || { echo "  cancelled"; return; }
    mkdir -p "$dir/logs"
    if [[ "$mode" == [bB] ]]; then
        nohup bash -c "$cmd" >"$log" 2>&1 &
        echo "  ${G}started pid $!${N}  ${D}(follow: tail -f $log)${N}"
    else
        bash -c "$cmd" 2>&1 | tee "$log"
        local rc=${PIPESTATUS[0]}
        if (( rc == 0 )); then echo "  ${G}done${N}"; else echo "  ${R}exit code $rc${N}"; fi
    fi
}

run_script() {  # run_script <paper>/<target>/<script.py>
    local rel=$1
    echo "  ${D}(Enter = default, q = back)${N}"
    params "$rel" || { echo "  cancelled"; return; }
    local s=${rel##*/}
    run_job "${s%.py}" "scripts/${rel%/*}" "$PY scripts/$rel$ARGS"
}

train_all() {
    local steps seed a log dir=scripts/aperiodic/train_ppo
    echo "  ${Y}Starts 4 background trainings (alpha 0, 0.25, 0.5, 0.75); each overwrites its checkpoint.${N}"
    ask steps "training steps (paper 1000000)" 1000000 || return
    ask seed "seed" 42 || return
    confirm "start?" || return
    mkdir -p "$dir/logs"
    for a in 0 0.25 0.5 0.75; do
        log="$dir/logs/train_ppo_alpha_${a}_$(date +%Y%m%d-%H%M%S).log"
        nohup "$PY" "$dir/train_ppo.py" --steps "$steps" --seed "$seed" --alpha "$a" >"$log" 2>&1 &
        echo "  ${G}alpha=$a pid $!${N}  ${D}$log${N}"
    done
}

pipeline() {
    local ep workers a cmd s=scripts/aperiodic
    echo "  Runs Fig. 4, 5 (+Table IV), 6, 7, 8, Tables V/VI, then validation; stops at the first error."
    ask ep "episodes (paper 100)" 100 || return
    ask workers "workers" "$NPROC" || return
    a="--episodes $ep --workers $workers"
    cmd="set -e; $PY $s/figure4/reproduce_fig4.py"
    for n in 5 6 7 8; do cmd+="; $PY $s/figure$n/reproduce_fig$n.py $a"; done
    cmd+="; $PY $s/tables/reproduce_tables.py $a; $PY $s/validation/validate.py"
    run_job pipeline "$s/validation" "$cmd"
}

all_logs() { ls -t scripts/*/*/logs/*.log 2>/dev/null; }

jobs_status() {
    local out
    out="$(pgrep -af 'scripts/.*\.py' | grep -v pgrep)"
    echo
    if [[ -n "$out" ]]; then echo "$out" | sed 's/^/  /'; else echo "  no script running"; fi
    echo "  ${D}latest logs:${N}"
    all_logs | head -5 | sed 's/^/    /'
}

tail_log() {
    local f
    f="$(all_logs | head -1)"
    [[ -z "$f" ]] && { echo "  no logs"; return; }
    echo "  ${D}$f  (Ctrl-C to stop)${N}"
    trap 'true' INT
    tail -n 30 -f "$f"
    trap - INT
}

# ---------------------------------------------------------------- menus

describe() {  # one-line description of a folder or script
    case "$1" in
        aperiodic) echo "3GPP Ambient IoT Inventory with Aperiodic Paging (Figs. 4-8, Tables IV-VI, PPO)" ;;
        periodic) echo "Fast Inventory ... Device Unavailability (Device-1 Fig. 5)" ;;
        aperiodic/figure4) echo "incident-power CDF, N_eff, type shares" ;;
        aperiodic/figure5) echo "single-source, aperiodic vs periodic, + Table IV" ;;
        aperiodic/figure6) echo "multi-source, aperiodic vs periodic" ;;
        aperiodic/figure7) echo "RL vs DFSA-Schoute vs CMEBE" ;;
        aperiodic/figure8) echo "resource efficiency vs N_tot" ;;
        aperiodic/tables) echo "Tables V (RL vs PFSA) and VI (alpha sweep)" ;;
        aperiodic/train_ppo) echo "Recurrent PPO training" ;;
        aperiodic/validation) echo "compare every result with the paper" ;;
        aperiodic/digitize) echo "extract Figs. 4-8 from the PDF into figure*/paper/" ;;
        periodic/fig5a) echo "p_in CDF used by the simulator" ;;
        periodic/fig5b) echo "EM vs DCM 1/4 groups: reproduce, validate, diagnose, digitize" ;;
        periodic/assumptions) echo "effect of assumptions the paper leaves open" ;;
        act:pipeline) echo "Figs. 4-8, Tables IV-VI, then validation, in one go" ;;
        act:train_all) echo "alpha 0 / 0.25 / 0.5 / 0.75 in the background" ;;
        *.py) awk 'f && NF { print; exit }
                   /"""/ { s = $0; sub(/^[^"]*"""/, "", s); sub(/""".*$/, "", s); sub(/\.$/, "", s)
                           if (length(s)) { print s; exit } f = 1 }' "scripts/$1" ;;
    esac
}

# pick "<title>" item... ; prints the menu, sets PICK to the chosen item; returns BACK on q
PICK=""
pick() {
    local title=$1; shift
    local items=("$@") i c
    while true; do
        echo
        echo "${B}$title${N}"
        for i in "${!items[@]}"; do
            printf "  %2d  %-22s ${D}%s${N}\n" $((i + 1)) "$(label "${items[$i]}")" "$(describe "$(key "${items[$i]}")")"
        done
        echo "  ${D} j  jobs + latest logs    l  follow latest log    q  back${N}"
        read -r -p "${B}> ${N}" c || return $BACK
        case "$c" in
            q | Q) return $BACK ;;
            j | J) jobs_status ;;
            l | L) tail_log ;;
            "") ;;
            *)
                if [[ "$c" =~ ^[0-9]+$ ]] && ((c >= 1 && c <= ${#items[@]})); then
                    PICK=${items[$((c - 1))]}
                    return 0
                fi
                echo "  ${R}unknown choice: $c${N}" ;;
        esac
    done
}

# items are "<kind>:<path>"; kind = dir | py | act
label() {
    local p=${1#*:}
    case "$1" in
        act:train_all) echo "train all 4 alphas" ;;
        act:pipeline) echo "full pipeline" ;;
        *) echo "${p##*/}" ;;
    esac
}
key() {
    case "$1" in
        act:*) echo "$1" ;;
        *) echo "${1#*:}" ;;
    esac
}

subdirs() { find "scripts/$1" -mindepth 1 -maxdepth 1 -type d ! -name '_*' ! -name '__pycache__' -printf '%f\n' | sort; }
pyfiles() { find "scripts/$1" -maxdepth 1 -type f -name '*.py' ! -name '_*' -printf '%f\n' | sort; }

target_menu() {  # <paper>/<target>
    local t=$1 items=() f
    for f in $(pyfiles "$t"); do items+=("py:$t/$f"); done
    [[ "$t" == aperiodic/train_ppo ]] && items+=("act:train_all")
    while pick "scripts/$t/" "${items[@]}"; do
        case "$PICK" in
            py:*) run_script "${PICK#py:}" ;;
            act:train_all) train_all ;;
        esac
    done
}

paper_menu() {  # <paper>
    local p=$1 items=() d
    for d in $(subdirs "$p"); do items+=("dir:$p/$d"); done
    [[ "$p" == aperiodic ]] && items+=("act:pipeline")
    while pick "scripts/$p/" "${items[@]}"; do
        case "$PICK" in
            dir:*) target_menu "${PICK#dir:}" ;;
            act:pipeline) pipeline ;;
        esac
    done
}

top_menu() {
    local items=() d
    for d in $(find scripts -mindepth 1 -maxdepth 1 -type d ! -name '_*' ! -name '__pycache__' -printf '%f\n' | sort); do
        items+=("dir:$d")
    done
    while pick "scripts/   ${D}python: $PY   cpus: $NPROC${N}" "${items[@]}"; do
        paper_menu "${PICK#dir:}"
    done
}

if [[ $# -ge 2 && -d "scripts/$1/$2" ]]; then
    target_menu "$1/$2"
elif [[ $# -ge 1 && -d "scripts/$1" ]]; then
    paper_menu "$1"
else
    top_menu
fi
