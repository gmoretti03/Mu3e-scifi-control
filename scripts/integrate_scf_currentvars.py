"""Fixes CurrentVars/Power/user_mask (a SHARED array indexed the same
as Setup/Power/Map - was left at length 21 after Setup/Power's SCF
block grew from 6 to 24, now misaligned) and adds SCF_HV_target/
SCF_VDD_target (SciFi-private arrays, mirroring VTX_HV_target/
VTX_VDD_target's own shape - one value per SCF partition, not shared-
indexed). Seeded with REAL current live values (HV/Variables/Demand,
DCDCCrates/Variables/"Voltage Adjust"), not invented targets - this is
CurrentVars, i.e. current state, not a tuned operating point nobody has
verified for SciFi yet.
"""
import re
import midas.client

client = midas.client.MidasClient("IntegrateScfCurrentVars", expt_name="Mu3e")

power = client.odb_get("/CosmicRun/Setup/Power")
subsystem = power["Map_Subsystem"]
vtx_end = subsystem.index("SCF")
sct_start = subsystem.index("SCT")
n_scf = sct_start - vtx_end

cv = client.odb_get("/CosmicRun/CurrentVars/Power")
user_mask = cv["user_mask"]
assert len(user_mask) == 21, "user_mask length assumption changed, aborting: " + str(len(user_mask))
cv["user_mask"] = user_mask[:vtx_end] + [False] * n_scf + user_mask[vtx_end + 6:]
assert len(cv["user_mask"]) == len(power["Map"]), "user_mask still misaligned with Setup/Power/Map"

hv_demand = client.odb_get("/Equipment/HV/Variables/Demand")
lv_voltage_adjust = client.odb_get("/Equipment/DCDCCrates/Variables/Voltage Adjust")
hv_board = client.odb_get("/Equipment/HV/Settings/Board")
lv_names = client.odb_get("/Equipment/DCDCCrates/Settings/Names")

# Re-derive the raw flat indices from the module label itself, same as
# integrate_scf_setup_power.py - NOT from Map_HV_Crate/Map_LV_Crate
# (those store the real hardware crate identifiers - MSCB Address for
# LV, Board number for HV - not a 0-based flat array index, so they
# can't be inverted back into one without redoing this lookup anyway).
lv_index_for_sm = {}
for i, n in enumerate(lv_names):
    m = re.match(r"^SMB_([A-Z]+)_(\d+)-(\d+)$", n) if isinstance(n, str) else None
    if m:
        lv_index_for_sm[(m.group(1), int(m.group(2)) // 2)] = i
hv_index_for_board = {b: i for i, b in enumerate(hv_board) if isinstance(b, str)}

hv_target = []
vdd_target = []
for label in power["Map"][vtx_end:sct_start]:
    lm = re.match(r"^SCF_([A-Z]+)_SM(\d+)_M\d+$", label)
    side, sm = lm.group(1), int(lm.group(2))
    lv_idx = lv_index_for_sm.get((side, sm))
    vdd_target.append(lv_voltage_adjust[lv_idx] if lv_idx is not None else 0.0)

for hv_crate, hv_channel in zip(power["Map_HV_Crate"][vtx_end:sct_start], power["Map_HV_Channel"][vtx_end:sct_start]):
    hv_idx = hv_index_for_board.get("S" + str(hv_crate) + "-" + str(hv_channel))
    hv_target.append(hv_demand[hv_idx] if hv_idx is not None else 0.0)

cv["SCF_HV_target"] = hv_target
cv["SCF_VDD_target"] = vdd_target

client.odb_set("/CosmicRun/CurrentVars/Power", cv, create_if_needed=True)
print("user_mask length now:", len(cv["user_mask"]))
print("SCF_HV_target:", hv_target[:6])
print("SCF_VDD_target:", vdd_target[:6])

client.disconnect()
