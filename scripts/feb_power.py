"""
PySequencer entry point: SciFi FEB-crate power on/off, on the new
scifi_scripts object model - replaces the original bulk feb_power.py for
SciFiFibre (no Labor support here). The actual logic (link_feb-indexed
FEBCrate[]/FEBSlot[] lookup, the CrateControllerConnected safety check)
lives in detector/feb.py's turn_on_feb_power()/turn_off_feb_power() -
this script is just the thin PySequencer bridge (register params -> set
common.setup flags -> call into detector/).
"""

import midas.client
import common.setup as setup
import detector.scifi as detector


def define_params(seq):
    seq.register_param("power_on", "True = power FEBs on, False = power off", True)
    seq.register_param("is_odb_available", "Is there a real, correct ODB on this machine", True)
    seq.register_param("can_send_commands_to_odb", "Actually write to ODB (False = dry run)", True)


def sequence(seq):
    power_on = seq.get_param("power_on")
    setup.is_odb_available = seq.get_param("is_odb_available")
    setup.can_send_commands_to_odb = seq.get_param("can_send_commands_to_odb")

    # Own MidasClient, not seq itself - detector/'s ODBCommand pattern expects
    # a real midas.client.MidasClient (client.odb_get/odb_set), a
    # different interface than PySequencer's own seq.odb_get/odb_set.
    # ALWAYS disconnect it explicitly (try/finally) - an ad-hoc client left
    # unclosed leaves a stale /Programs/<name> ODB record that MIDAS's
    # alarm system then repeatedly flags (happened once already - never
    # again).
    client = midas.client.MidasClient("SciFiScripts_FebPower")
    try:
        det = detector.SciFiDetector(client)
        if not det.febs:
            seq.msg("No active SciFi (Fibre-type) FEBs found in LinksFibre - nothing to power", is_error=True)
            return

        done, skipped = det.turn_on_all_feb_power() if power_on else det.turn_off_all_feb_power()

        action = "on" if power_on else "off"
        seq.msg(f"Power {action}: {len(done)}/{len(det.febs)} SciFi FEB(s) switched ({done})")
        if skipped:
            seq.msg(f"Skipped {len(skipped)} FEB(s): {skipped}", is_error=True)

        if power_on and done:
            # Informational only, no pass/fail judgement - see
            # Feb.get_power_monitoring()'s own docstring for why.
            for feb_index in done:
                monitoring = det.febs[feb_index].get_power_monitoring()
                if monitoring:
                    seq.msg(f"Feb {feb_index} monitoring: {monitoring}")
    finally:
        client.disconnect()
