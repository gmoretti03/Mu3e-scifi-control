"""Loads the ENTIRE real /CosmicRun tree (Setup, CurrentVars,
Calibration, CalibrationDefaults, OperationMode, Conditions, Tuning,
CustomRun, Tmp - all of pixel's real VTX content) from the real ODB
dump onto the local test experiment, so SciFi's own entries can be
integrated into it alongside real pixel data instead of in isolation.
Written 2026-08-07 (user: "caricare CosmicRun sul mio odb locale e poi
integriamo tutto quello che c'e' da integrare per scifi"). Merges
in-memory before writing so it does NOT clobber whatever SciFi content
already exists under Calibration/SciFi (odb_set's remove_unspecified_
keys=True would otherwise delete it, since the dump only has VTX
there) - re-reads the current local Calibration/SciFi tree first and
folds it back in. Run so far ONLY against the local test experiment -
never against mu3ebe."""
import json
import midas.client

DUMP_PATH = "/Users/gmoretti/Work/Mu3e/Docs/devolpment/old/odb_070826_134730.json"

def strip_keys(d):
    if isinstance(d, dict):
        return {k: strip_keys(v) for k, v in d.items() if not k.endswith("/key")}
    return d

with open(DUMP_PATH) as f:
    dump = json.load(f)

real_cosmicrun = strip_keys(dump["CosmicRun"])

client = midas.client.MidasClient("LoadCosmicRun", expt_name="Mu3e")

existing_scifi_calibration = client.odb_get("/CosmicRun/Calibration/SciFi")
real_cosmicrun.setdefault("Calibration", {})["SciFi"] = existing_scifi_calibration

for branch, content in real_cosmicrun.items():
    client.odb_set("/CosmicRun/" + branch, content, create_if_needed=True)
    print("Written /CosmicRun/" + branch)

print()
print("=== verify SciFi still present under Calibration ===")
print(list(client.odb_get("/CosmicRun/Calibration").keys()))
print()
print("=== verify VTX now present ===")
print(list(client.odb_get("/CosmicRun/Calibration").keys()))
print(list(client.odb_get("/CosmicRun/CalibrationDefaults").keys()))

client.disconnect()
