import midas.client

client = midas.client.MidasClient("RebuildScanThrDefaultsTemplate", expt_name="Mu3e")

# 2026-08-11: settle_seconds and threshold_step moved out of per-ASIC
# ParametersUsed - both are now real shared top-level ScanThr/ fields
# (siblings of selected_asics), not per-ASIC defaults, so neither
# belongs in this per-ASIC template any more.
template = {
    "Status": "Never run",
    "Message": "",
    "ParametersUsed": {
        "threshold_start": 0, "threshold_stop": 63, "offset_start": 0, "offset_end": 2,
        "noisy_rate_threshold": 1000000, "run_thr_finding": False
    },
    "Output": {
        "n_step": 0, "n_thr": 0, "n_offset": 0, "fccr": [0.0] * 32
    },
    "ThrResult": {
        pe: {
            "chosen_offset": [0] * 32, "chosen_threshold": [0] * 32,
            "chosen_width": [0] * 32, "chosen_score": [0.0] * 32
        }
        for pe in ["Pe0_5", "Pe1_5", "Pe2_5"]
    },
    "Warnings": ""
}

old = client.odb_get("/CosmicRun/CalibrationDefaults/SciFi/ScanThr")
print("Old flat keys:", list(old.keys()))

client.odb_delete("/CosmicRun/CalibrationDefaults/SciFi/ScanThr")
client.odb_set("/CosmicRun/CalibrationDefaults/SciFi/ScanThr", template, create_if_needed=True)
print("Rebuilt as single non-partitioned template, matching ScanVbr's own pattern.")

client.disconnect()
