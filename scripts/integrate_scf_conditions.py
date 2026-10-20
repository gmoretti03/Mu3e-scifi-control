"""Adds SCF_-prefixed Conditions keys (watchdog thresholds), mirroring
every VTX_ field name exactly, but with NEUTRAL PLACEHOLDER values only
- NOT real thresholds. No verified real hardware limits exist for SciFi
yet, and populating these with guessed numbers would be actively unsafe
if anything ever reads them for real. This just establishes the schema
(field names + array lengths matching SCF_n_partitions=24) for later,
per the user's explicit instruction: "metti solo i nomi per scifi
senza valore".
"""
import midas.client

client = midas.client.MidasClient("IntegrateScfConditions", expt_name="Mu3e")

power = client.odb_get("/CosmicRun/Setup/Power")
n_scf = power["SCF_n_partitions"]

cond = client.odb_get("/CosmicRun/Conditions")

cond["SCF_Max_HV_voltage"] = [0.0] * n_scf
cond["SCF_Monitor_Max_HV_current"] = [0.0] * n_scf
cond["SCF_Monitor_Max_HV_curr_read"] = [0.0] * n_scf
cond["SCF_Monitor_Max_LV_current"] = [0.0] * n_scf
cond["SCF_Validate_Max_PP_On"] = 0
cond["SCF_Setup_DCDC_Output_voltage"] = 0.0
cond["SCF_Monitor_Max_VDD_voltage"] = 0.0
cond["SCF_Monitor_Min_VDD_voltage"] = 0.0
cond["SCF_Monitor_Max_Temperature"] = 0.0
cond["SCF_Monitor_Warn_Temperature"] = 0.0
cond["SCF_Monitor_Min_Temperature"] = 0.0
cond["SCF_Monitor_TDK"] = ""
cond["SCF_Monitor_TDK_Voltage"] = 0.0
cond["SCF_Monitor_PwrDistCrates"] = False
cond["SCF_Monitor_PwrDistPixel"] = False
cond["SCF_Validate_Conf_Min_LV_curr"] = [0.0] * n_scf
cond["SCF_Conf_Max_Chips_Min_LV_curr"] = [0] * n_scf

client.odb_set("/CosmicRun/Conditions", cond, create_if_needed=True)
print("Written", sum(1 for k in cond if k.startswith("SCF_")), "SCF_ Conditions keys (all placeholder values)")

client.disconnect()
