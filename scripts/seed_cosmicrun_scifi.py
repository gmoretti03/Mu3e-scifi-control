"""Creates /CosmicRun/Calibration/SciFi/ScanVbr (+ CurrentCalibration)
from scratch, one folder per real module with the ODB results structure
from calibration_process.txt, matching the real HV_BOARDS mapping and
real LinksFibre FEB data - no invented values. Written 2026-08-07
because MIDAS's db_paste (what the page's modbset() uses) requires the
target key to already exist - it does NOT create missing paths like the
Python client's odb_set(create_if_needed=True) does, so the page's
Start button silently failed to write anything against an empty tree.

ScanThr is NOT seeded here - see seed_scanthr.py, the dedicated,
currently-correct per-ASIC seeder for it. It used to be seeded here
too (a flat, wrong-shaped stub, pre-dating ScanThr's real per-ASIC
page/schema), but that seeding is gone as of 2026-08-11: odb_set()'s
default remove_unspecified_keys=True means writing a scoped-down dict
under /CosmicRun/Calibration/SciFi would have DELETED every real
per-ASIC ScanThr folder seed_scanthr.py had built, replacing it with
that flat 7-field stub - found during a pre-mu3ebe-deployment audit,
never actually run against mu3ebe, but its own docstring said it
eventually would be. Every odb_set() call below is scoped to exactly
the subtree it owns (ScanVbr, CurrentCalibration) and passes
remove_unspecified_keys=False, so re-running this never touches
ScanThr or anything else under Calibration/SciFi.

Run once against any experiment that doesn't have this tree yet. Run
so far ONLY against the local test experiment (mhttpd -D) - never
against mu3ebe. To eventually load onto the real system, this same
script would need to be run there instead, by the user themself -
change expt_name/host_name as needed for wherever it's meant to run."""
import re
import midas.client

client = midas.client.MidasClient("SeedCosmicRunScifi", expt_name="Mu3e")

FEBTYPE_FIBRE = 3

HV_BOARDS = [
    {"label": "US Top", "namesBase": 20, "modules": [None, None, 2, 3, 4, 5, 6, 7]},
    {"label": "US Bottom", "namesBase": 72, "modules": [None, None, 8, 9, 10, 11, 0, 1]},
    {"label": "DS Top", "namesBase": 132, "modules": [None, None, 2, 3, 4, 5, 6, 7]},
    {"label": "DS Bottom", "namesBase": 188, "modules": [10, 11, 0, 1, None, None, 8, 9]},
]

def hv_index_for_module(side, module_number):
    for board in HV_BOARDS:
        if not board["label"].startswith(side):
            continue
        if module_number in board["modules"]:
            return board["namesBase"] + board["modules"].index(module_number)
    return None

feb_type = client.odb_get("/Equipment/LinksFibre/Settings/FEBType")
feb_name = client.odb_get("/Equipment/LinksFibre/Settings/FEBName")
hv_names = client.odb_get("/Equipment/HV/Settings/Names")

modules = []
for feb_index, t in enumerate(feb_type):
    if t != FEBTYPE_FIBRE:
        continue
    m = re.match(r"^([A-Z]+) SM (\d+)$", feb_name[feb_index])
    if not m:
        continue
    side, sm = m.group(1), int(m.group(2))
    for local_m in (0, 1):
        real_module = 2 * sm + local_m
        label = side + "_SM" + str(sm) + "_M" + str(real_module)
        hv_idx = hv_index_for_module(side, real_module)
        hv_channel = hv_names[hv_idx] if hv_idx is not None else ""
        modules.append({"label": label, "hv_channel": hv_channel})

print("Resolved", len(modules), "modules:")
for mod in modules:
    print(" ", mod["label"], "->", mod["hv_channel"])

# iv_start/iv_end/run_vbr_finding/fit_window_v/min_peak_prominence are
# per-module ParametersUsed defaults. iv_increment/settle_seconds are
# real shared top-level ScanVbr/ fields (siblings of selected_modules),
# NOT per-module - moved out during this session's shared-field refactor
# (2026-08-11), see calibration_open_items.txt section 1.
iv_param_defaults = {
    "iv_start": 54.0, "iv_end": 58.0,
    "run_vbr_finding": False, "fit_window_v": 0.5, "min_peak_prominence": 3.0,
}

scan_vbr_tree = {
    "selected_channels": "",
    "selected_modules": "",
    "iv_increment": 2.0,
    "settle_seconds": 5,
    "Status": "Never run",
    "Message": "",
}
for mod in modules:
    scan_vbr_tree[mod["label"]] = {
        "HVChannel": mod["hv_channel"],
        "Status": "Never run",
        "Message": "",
        "ParametersUsed": dict(iv_param_defaults),
        "Output": {
            "Voltage": 0.0,
            "Current": 0.0,
            "Temperature": 0.0,
        },
        "VbrResult": {
            "Found": False,
            "Confident": False,
            "FitFailed": False,
            "VBreakdownRaw": 0.0,
            "IBreakdown": 0.0,
            "VBreakdownFit": 0.0,
            "FitSigma": 0.0,
        },
        "Warnings": "",
    }

client.odb_set("/CosmicRun/Calibration/SciFi/CurrentCalibration", "ScanVbr",
                create_if_needed=True, remove_unspecified_keys=False)
print("Written /CosmicRun/Calibration/SciFi/CurrentCalibration")

client.odb_set("/CosmicRun/Calibration/SciFi/ScanVbr", scan_vbr_tree,
                create_if_needed=True, remove_unspecified_keys=False)
print("Written /CosmicRun/Calibration/SciFi/ScanVbr (ScanThr untouched - see seed_scanthr.py)")

client.disconnect()
