"""DCDCCrates/Variables/Temperature was never seeded - all 128 raw
entries read the sentinel -999.0, showing as a clearly-broken "-999.0C"
in Geometry's LV block. Set only the real SciFi (SMB_/LDO_-named)
channels to a sane spread, same 28-35C convention used for the earlier
SFFE temperature seeding this session - leaving every other
subsystem's channel untouched (not ours to seed).
"""
import midas.client

client = midas.client.MidasClient("FixDcdcTemperature", expt_name="Mu3e")

names = client.odb_get("/Equipment/DCDCCrates/Settings/Names")
temps = client.odb_get("/Equipment/DCDCCrates/Variables/Temperature")

scifi_indices = [i for i, n in enumerate(names) if isinstance(n, str) and (n.startswith("SMB_") or n.startswith("LDO_"))]
print("SciFi SMB_/LDO_ channels found:", len(scifi_indices))

for j, i in enumerate(scifi_indices):
    temps[i] = round(28.0 + (j % 8), 1)

client.odb_set("/Equipment/DCDCCrates/Variables/Temperature", temps, create_if_needed=True)
print("Updated", len(scifi_indices), "SciFi channels, e.g.:", [(names[i], temps[i]) for i in scifi_indices[:5]])

client.disconnect()
