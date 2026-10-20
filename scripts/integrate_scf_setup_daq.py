"""Fixes Setup/DAQ's SCF_n_FEBs (was 2, a wrong old placeholder - the
real count, confirmed live from LinksFibre/Settings/FEBType, is 12, not
to be confused with the 24 MODULES - 2 per Feb - used everywhere else
this session). Adds SCF_Map/SCF_Map_FEB/SCF_Map_Position_on_FEB,
mirroring VTX_Map's own per-ladder mapping shape but for SciFi's real
sub-Feb unit (ASIC, not ladder) - one entry per ACTUALLY ENABLED ASIC
position (from the real ASICMask), same "only list what's really
there" convention VTX_Map itself already uses (some Febs there only
have 3 ladders, not a fixed 4).
"""
import re
import midas.client

client = midas.client.MidasClient("IntegrateScfSetupDaq", expt_name="Mu3e")

FEBTYPE_FIBRE = 3

feb_type = client.odb_get("/Equipment/LinksFibre/Settings/FEBType")
feb_name = client.odb_get("/Equipment/LinksFibre/Settings/FEBName")
num_asics_max = client.odb_get("/Equipment/LinksFibre/Settings/NumASICsMax")
asic_mask = client.odb_get("/Equipment/LinksFibre/Settings/ASICMask")

scf_map, scf_map_feb, scf_map_pos = [], [], []
scf_feb_index = 0
for feb_index, t in enumerate(feb_type):
    if t != FEBTYPE_FIBRE:
        continue
    m = re.match(r"^([A-Z]+) SM (\d+)$", feb_name[feb_index])
    side, sm = m.group(1), m.group(2)
    n_asics = num_asics_max[feb_index] if isinstance(num_asics_max[feb_index], int) else int(num_asics_max[feb_index], 16)
    mask = asic_mask[feb_index] if isinstance(asic_mask[feb_index], int) else int(asic_mask[feb_index], 16)
    for pos in range(n_asics):
        if ((mask >> pos) & 1) == 1:
            scf_map.append("SCF_" + side + "_SM" + sm + "_A" + str(pos + 1))
            scf_map_feb.append(scf_feb_index)
            scf_map_pos.append(pos)
    scf_feb_index += 1

n_real_febs = scf_feb_index
print("Real SciFi FEB count:", n_real_febs, "(NOT 24 - that's modules, 2 per Feb)")
print("Real enabled-ASIC map entries:", len(scf_map))
for entry in scf_map:
    print(" ", entry)

daq = client.odb_get("/CosmicRun/Setup/DAQ")
old_scf_n_febs = daq["SCF_n_FEBs"]
daq["SCF_n_FEBs"] = n_real_febs
daq["n_tot_FEBs"] = daq["VTX_n_FEBs"] + daq["SCF_n_FEBs"] + daq["SCT_n_FEBs"]
daq["SCF_n_asic_partitions"] = len(scf_map)
daq["SCF_Map"] = scf_map
daq["SCF_Map_FEB"] = scf_map_feb
daq["SCF_Map_Position_on_FEB"] = scf_map_pos

client.odb_set("/CosmicRun/Setup/DAQ", daq, create_if_needed=True)
print()
print("SCF_n_FEBs:", old_scf_n_febs, "->", daq["SCF_n_FEBs"])
print("n_tot_FEBs now:", daq["n_tot_FEBs"])
print("VTX_n_FEBs unchanged?", daq["VTX_n_FEBs"] == 10)
print("VTX_Map unchanged, len:", len(daq["VTX_Map"]))

client.disconnect()
