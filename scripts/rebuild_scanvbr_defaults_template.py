import midas.client

client = midas.client.MidasClient("RebuildScanVbrDefaultsTemplate", expt_name="Mu3e")

# 2026-08-11: iv_step (per-module) was renamed/moved to iv_increment, a
# real shared top-level ScanVbr/ field (sibling of selected_modules),
# same move as ScanThr's settle_seconds/threshold_step - neither
# iv_increment nor settle_seconds belongs in this per-module template
# any more. Also added Output/Temperature (SiPM chiller reading,
# written live during execute()).
template = {
    "Status": "Never run",
    "Message": "",
    "ParametersUsed": {
        "iv_start": 54.0, "iv_end": 58.0,
        "run_vbr_finding": False, "fit_window_v": 0.5, "min_peak_prominence": 3.0
    },
    "Output": {
        "Voltage": 0.0, "Current": 0.0, "Temperature": 0.0
    },
    "VbrResult": {
        "Found": False, "Confident": False, "FitFailed": False,
        "VBreakdownRaw": 0.0, "IBreakdown": 0.0, "VBreakdownFit": 0.0, "FitSigma": 0.0
    },
    "Warnings": ""
}

old = client.odb_get("/CosmicRun/CalibrationDefaults/SciFi/ScanVbr")
print("Old flat keys:", list(old.keys()))

client.odb_delete("/CosmicRun/CalibrationDefaults/SciFi/ScanVbr")
client.odb_set("/CosmicRun/CalibrationDefaults/SciFi/ScanVbr", template, create_if_needed=True)
print("Rebuilt as single non-partitioned template, matching ScanThr's own pattern.")

client.disconnect()
