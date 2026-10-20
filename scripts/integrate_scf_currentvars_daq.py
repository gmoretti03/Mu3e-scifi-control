"""Adds SCF_chip_user_enabled (BOOL[96]) to CurrentVars/DAQ, the SciFi
analog of VTX_chip_user_enabled. Real precedent checked in
pixel_scripts/core/detector.py (assign_chips_to_febs) and chip.py
(get_config_id): VTX_chip_user_enabled is BOOL[108] = 36 ladders
(VTX_Map) x 3 chips/ladder, because VTX_Map is ladder-granularity and
the pixel code multiplies by 3 chips/ladder on the fly to build the
per-chip config id.

SciFi has no such extra level: SCF_Map is already ASIC (=chip)
granularity (96 entries, one per real enabled ASIC). So
SCF_chip_user_enabled is a straight 1:1 BOOL[96] against SCF_Map, no
x3 multiplication needed.

No consumer exists yet for this key - scifi_scripts hasn't been
migrated to the detector/chip framework that reads
VTX_chip_user_enabled (that migration is planned but not started).
Added now per explicit instruction to pre-populate ODB structure ahead
of that future work, all entries default False (no chips selected),
same as a fresh/unconfigured state.
"""
import midas.client

client = midas.client.MidasClient("IntegrateScfCurrentVarsDaq", expt_name="Mu3e")

daq_setup = client.odb_get("/CosmicRun/Setup/DAQ")
n_scf_chips = len(daq_setup["SCF_Map"])

cv_daq = client.odb_get("/CosmicRun/CurrentVars/DAQ")
cv_daq["SCF_chip_user_enabled"] = [False] * n_scf_chips

client.odb_set("/CosmicRun/CurrentVars/DAQ", cv_daq, create_if_needed=True)
print("SCF_chip_user_enabled written, length:", len(cv_daq["SCF_chip_user_enabled"]))
print("VTX_chip_user_enabled unchanged, length:", len(cv_daq["VTX_chip_user_enabled"]))

client.disconnect()
