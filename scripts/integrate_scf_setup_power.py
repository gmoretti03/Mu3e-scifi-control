"""Expands CosmicRun/Setup/Power's SCF (SciFi) block from 6 placeholder
rows to 24 real ones (one per real module), using real data only:
- LV crate = DCDCCrates MSCB Address for that module's SM-pair device,
  LV channel = raw Names[] index % Channels-per-device(16)
- HV crate/channel = parsed from the real Board field ("S30-1" -> 30, 1)
- HV_Type = "HVboxN", same real class name as pixel's own HVBoxNPowerSupply
- LV_Type = "DCDC", same as pixel
- Number_of_ASICs = real per-module active ASIC count from LinksFibre
No VTX_Resistivity equivalent (pixel-chip-specific, doesn't apply to
SiPMs) and no Map_MPDC (never seen used for SciFi anywhere this
session - looks pixel-specific) - left as 0/not-applicable for SciFi
rows, VTX/SCT rows untouched.
"""
import re
import midas.client

client = midas.client.MidasClient("IntegrateScfSetupPower", expt_name="Mu3e")

FEBTYPE_FIBRE = 3
LV_CHANNELS_PER_DEVICE = 16

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
num_asics_max = client.odb_get("/Equipment/LinksFibre/Settings/NumASICsMax")
asic_mask = client.odb_get("/Equipment/LinksFibre/Settings/ASICMask")

hv_names = client.odb_get("/Equipment/HV/Settings/Names")
hv_board = client.odb_get("/Equipment/HV/Settings/Board")

lv_names = client.odb_get("/Equipment/DCDCCrates/Settings/Names")
lv_mscb_addr = client.odb_get("/Equipment/DCDCCrates/Settings/MSCB Address")

lv_index_for_sm = {}
for i, n in enumerate(lv_names):
    m = re.match(r"^SMB_([A-Z]+)_(\d+)-(\d+)$", n) if isinstance(n, str) else None
    if not m:
        continue
    side, sm = m.group(1), int(m.group(2)) // 2
    lv_index_for_sm[(side, sm)] = i

rows = []
for feb_index, t in enumerate(feb_type):
    if t != FEBTYPE_FIBRE:
        continue
    m = re.match(r"^([A-Z]+) SM (\d+)$", feb_name[feb_index])
    if not m:
        continue
    side, sm = m.group(1), int(m.group(2))
    n_asics = int(num_asics_max[feb_index], 16) if isinstance(num_asics_max[feb_index], str) else num_asics_max[feb_index]
    mask = int(asic_mask[feb_index], 16) if isinstance(asic_mask[feb_index], str) else asic_mask[feb_index]

    lv_idx = lv_index_for_sm.get((side, sm))
    lv_crate = lv_mscb_addr[lv_idx // LV_CHANNELS_PER_DEVICE] if lv_idx is not None else 0
    lv_channel = (lv_idx % LV_CHANNELS_PER_DEVICE) if lv_idx is not None else 0

    for local_m in (0, 1):
        real_module = 2 * sm + local_m
        label = "SCF_" + side + "_SM" + str(sm) + "_M" + str(real_module)

        asic_start = local_m * 4
        n_asics_this_module = sum(
            1 for a in range(4)
            if (asic_start + a) < n_asics and ((mask >> (asic_start + a)) & 1) == 1
        )

        hv_idx = hv_index_for_module(side, real_module)
        hv_crate, hv_channel = 0, 0
        if hv_idx is not None:
            board = hv_board[hv_idx]
            bm = re.match(r"^S(\d+)-(\d+)$", board)
            if bm:
                hv_crate, hv_channel = int(bm.group(1)), int(bm.group(2))

        rows.append({
            "label": label, "lv_crate": lv_crate, "lv_channel": lv_channel,
            "hv_crate": hv_crate, "hv_channel": hv_channel,
            "n_asics": n_asics_this_module,
        })

print("Built", len(rows), "real SCF rows:")
for r in rows:
    print(" ", r)

power = client.odb_get("/CosmicRun/Setup/Power")
subsystem = power["Map_Subsystem"]

vtx_end = len(subsystem) - subsystem[::-1].index("VTX")
sct_start = subsystem.index("SCT")
assert subsystem[vtx_end:sct_start] == ["SCF"] * (sct_start - vtx_end), "unexpected block boundaries, aborting"

def rebuild(field, new_values):
    return power[field][:vtx_end] + new_values + power[field][sct_start:]

power["Map"] = rebuild("Map", [r["label"] for r in rows])
power["Map_Subsystem"] = rebuild("Map_Subsystem", ["SCF"] * len(rows))
power["Map_LV_Crate"] = rebuild("Map_LV_Crate", [r["lv_crate"] for r in rows])
power["Map_LV_Channel"] = rebuild("Map_LV_Channel", [r["lv_channel"] for r in rows])
power["Map_LV_Type"] = rebuild("Map_LV_Type", ["DCDC"] * len(rows))
power["Map_HV_Crate"] = rebuild("Map_HV_Crate", [r["hv_crate"] for r in rows])
power["Map_HV_Channel"] = rebuild("Map_HV_Channel", [r["hv_channel"] for r in rows])
power["Map_HV_Type"] = rebuild("Map_HV_Type", ["HVboxN"] * len(rows))
power["Number_of_ASICs"] = rebuild("Number_of_ASICs", [r["n_asics"] for r in rows])
power["Map_MPDC_Crate"] = rebuild("Map_MPDC_Crate", [0] * len(rows))
power["Map_MPDC_Channel"] = rebuild("Map_MPDC_Channel", [0] * len(rows))
power["SCF_n_partitions"] = len(rows)
power["n_tot_partitions"] = len(power["Map"])

client.odb_set("/CosmicRun/Setup/Power", power, create_if_needed=True)
print()
print("Written. New n_tot_partitions =", power["n_tot_partitions"], "SCF_n_partitions =", power["SCF_n_partitions"])

client.disconnect()
