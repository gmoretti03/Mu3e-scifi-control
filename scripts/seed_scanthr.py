import re
import midas.client

client = midas.client.MidasClient("SeedScanThr", expt_name="Mu3e")

FEBTYPE_FIBRE = 3
BASE = "/CosmicRun/Calibration/SciFi/ScanThr"

feb_type = client.odb_get("/Equipment/LinksFibre/Settings/FEBType")
feb_name = client.odb_get("/Equipment/LinksFibre/Settings/FEBName")
num_asics_max = client.odb_get("/Equipment/LinksFibre/Settings/NumASICsMax")
asic_mask = client.odb_get("/Equipment/LinksFibre/Settings/ASICMask")

# settle_seconds/threshold_step are real shared top-level ScanThr/
# fields (siblings of selected_asics), not per-ASIC defaults - moved
# out during this session's shared-field refactor (2026-08-11).
params_defaults = {
    "threshold_start": 0, "threshold_stop": 63, "offset_start": 0, "offset_end": 2,
    "noisy_rate_threshold": 1000000, "run_thr_finding": False
}

# Live scan-position status, continuously overwritten during the
# measurement (not an archive of every point - matches ScanVbr's own
# Voltage/Current/Temperature live scalars). n_thr/n_offset are the
# threshold/offset value currently being applied to the WHOLE array
# (tthresh/tthresh_offset are written globally, not per-channel, so
# these are shared across every channel on the ASIC at any instant).
# fccr is the live per-channel rate readback, mirrored here from
# SciFiFibre/Variables/FCCR so everything relevant to this scan is in
# one place.
output_defaults = {
    "n_step": 0, "n_thr": 0, "n_offset": 0, "fccr": [0.0] * 32
}

# One subfolder per PE_BANDS entry in calibrations/thr_find.py
# (run_threshold_finding() always runs all 3 - no operator choice) -
# each channel can get a different chosen_offset/threshold per PE level.
thr_result_defaults = {
    pe: {
        "chosen_offset": [0] * 32, "chosen_threshold": [0] * 32,
        "chosen_width": [0] * 32, "chosen_score": [0.0] * 32
    }
    for pe in ["Pe0_5", "Pe1_5", "Pe2_5"]
}

count = 0
for feb_index, t in enumerate(feb_type):
    if t != FEBTYPE_FIBRE:
        continue
    m = re.match(r"^([A-Z]+) SM (\d+)$", feb_name[feb_index])
    side, sm = m.group(1), int(m.group(2))
    n_asics = num_asics_max[feb_index] if isinstance(num_asics_max[feb_index], int) else int(num_asics_max[feb_index], 16)
    mask = asic_mask[feb_index] if isinstance(asic_mask[feb_index], int) else int(asic_mask[feb_index], 16)
    for asic_pos in range(n_asics):
        if ((mask >> asic_pos) & 1) != 1:
            continue
        module_of_pair = asic_pos // 4
        asic_in_module = asic_pos % 4
        real_module = 2 * sm + module_of_pair
        folder = side + "_SM" + str(sm) + "_M" + str(real_module) + "_A" + str(asic_in_module)
        entry = {
            "Status": "Never run",
            "Message": "",
            "ParametersUsed": dict(params_defaults),
            "Output": dict(output_defaults),
            "ThrResult": dict(thr_result_defaults),
            "Warnings": ""
        }
        client.odb_set(BASE + "/" + folder, entry, create_if_needed=True)
        count += 1

print("Seeded", count, "ASIC folders under", BASE)
client.disconnect()
