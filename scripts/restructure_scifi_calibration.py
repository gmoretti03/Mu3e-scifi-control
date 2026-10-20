"""Moves ScanThr/ScanVbr (params + all 24 modules) from Calibration/
SciFi to CalibrationDefaults/SciFi, matching the real convention found
in CalibrationDefaults/VTX/IVScan (Calibration branch = bare selector
only, CalibrationDefaults = actual params/state/output). Run once
against the local test experiment."""
import midas.client

client = midas.client.MidasClient("RestructureScifiCalibration", expt_name="Mu3e")

scan_thr = client.odb_get("/CosmicRun/Calibration/SciFi/ScanThr")
scan_vbr = client.odb_get("/CosmicRun/Calibration/SciFi/ScanVbr")

client.odb_set("/CosmicRun/CalibrationDefaults/SciFi", {"ScanThr": scan_thr, "ScanVbr": scan_vbr}, create_if_needed=True)
print("Written /CosmicRun/CalibrationDefaults/SciFi/{ScanThr,ScanVbr}")

client.odb_delete("/CosmicRun/Calibration/SciFi/ScanThr")
client.odb_delete("/CosmicRun/Calibration/SciFi/ScanVbr")
print("Deleted old Calibration/SciFi/{ScanThr,ScanVbr}")

print()
print("=== Calibration/SciFi now ===")
print(list(client.odb_get("/CosmicRun/Calibration/SciFi").keys()))
print("=== CalibrationDefaults/SciFi now ===")
print(list(client.odb_get("/CosmicRun/CalibrationDefaults/SciFi").keys()))
print("=== module count under CalibrationDefaults/SciFi/ScanVbr ===")
vbr = client.odb_get("/CosmicRun/CalibrationDefaults/SciFi/ScanVbr")
print(sum(1 for k in vbr if "_SM" in k))

client.disconnect()
