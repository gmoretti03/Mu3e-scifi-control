"""Moves ScanVbr's REAL per-module state from CalibrationDefaults/SciFi
(where it was originally built, under a wrong assumption about the
Calibration/CalibrationDefaults split) to Calibration/SciFi - matching
the real precedent found in Calibration/VTX/VDAC_power_consumption
(real per-partition Parameters/CurrentState/Output/Running, live data)
vs CalibrationDefaults/VTX/VDAC_power_consumption (one single
non-partitioned default template, same shape). CalibrationDefaults/
SciFi/ScanVbr is rebuilt as that single default template instead.

selected_channels moves too - it's scan-instance-wide (not per
module), same role as VDAC's real Config_ID_per_pp/Config_ID_per_ladder
which live as siblings of the partition dirs directly under
Calibration/VTX/VDAC_power_consumption, not under CalibrationDefaults.
"""
import midas.client

client = midas.client.MidasClient("RestructureScanVbrToCalibration", expt_name="Mu3e")

OLD_BASE = "/CosmicRun/CalibrationDefaults/SciFi/ScanVbr"
NEW_REAL_BASE = "/CosmicRun/Calibration/SciFi/ScanVbr"
NEW_DEFAULTS_BASE = "/CosmicRun/CalibrationDefaults/SciFi/ScanVbr"

old_tree = client.odb_get(OLD_BASE)

module_folders = [k for k, v in old_tree.items() if isinstance(v, dict)]
print("Modules found under old location:", len(module_folders))

for folder in module_folders:
    client.odb_set(NEW_REAL_BASE + "/" + folder, old_tree[folder], create_if_needed=True)
print("Copied", len(module_folders), "module folders to", NEW_REAL_BASE)

client.odb_set(NEW_REAL_BASE + "/selected_channels", old_tree["selected_channels"], create_if_needed=True)
print("Copied selected_channels to", NEW_REAL_BASE)

client.odb_delete(OLD_BASE)
print("Deleted old tree at", OLD_BASE)

sample = old_tree[module_folders[0]]
default_template = {
    "Status": "Never run",
    "Message": "",
    "ParametersUsed": sample["ParametersUsed"],
    "Output": {k: 0 for k in sample["Output"]},
    "VbrResult": {k: (False if isinstance(v, bool) else 0) for k, v in sample["VbrResult"].items()},
    "Warnings": "",
}
client.odb_set(NEW_DEFAULTS_BASE, default_template, create_if_needed=True)
print("Created single non-partitioned default template at", NEW_DEFAULTS_BASE)

client.disconnect()
