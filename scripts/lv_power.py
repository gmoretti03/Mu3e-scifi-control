"""
PySequencer entry point: SciFi LV (DCDCCrates) power on/off, on the new
scifi_scripts object model - replaces the original bulk lv_power.py.
DCDCCrates has no Labor/Fibre split (single tree, shared by the whole
detector).

Each Feb owns its own LV channel directly (detector/feb.py, confirmed
1:1 with FEB/super-module), so this script just loops over
SciFiDetector.febs instead of pattern-matching Names[] like the
original script does.
"""

import midas.client
import common.setup as setup
import detector.scifi as detector

DEFAULT_LV_EXPECTED_CURRENT_A = 6.5  # UNVERIFIED, see module docstring
DEFAULT_LV_CURRENT_TOLERANCE_A = 3.0


def define_params(seq):
    seq.register_param("power_on", "True = power LV on, False = power off", True)
    seq.register_param(
        "settle_seconds",
        "Wait this long after powering on before checking Current (real settle time unverified - adjust as needed)",
        5,
    )
    seq.register_param(
        "expected_current_a",
        f"Expected Current per channel in Amps once settled (UNVERIFIED default {DEFAULT_LV_EXPECTED_CURRENT_A}A, "
        "adjust once real values are known)",
        DEFAULT_LV_EXPECTED_CURRENT_A,
    )
    seq.register_param(
        "current_tolerance_a",
        f"+/- tolerance around expected_current_a before flagging a channel (UNVERIFIED default {DEFAULT_LV_CURRENT_TOLERANCE_A}A)",
        DEFAULT_LV_CURRENT_TOLERANCE_A,
    )
    seq.register_param("is_odb_available", "Is there a real, correct ODB on this machine", True)
    seq.register_param("can_send_commands_to_odb", "Actually write to ODB (False = dry run)", True)


def sequence(seq):
    power_on = seq.get_param("power_on")
    settle_seconds = seq.get_param("settle_seconds")
    expected_current_a = seq.get_param("expected_current_a")
    current_tolerance_a = seq.get_param("current_tolerance_a")
    setup.is_odb_available = seq.get_param("is_odb_available")
    setup.can_send_commands_to_odb = seq.get_param("can_send_commands_to_odb")

    # Own MidasClient, always disconnected via try/finally - see
    # scripts/feb_power.py's module docstring for why.
    client = midas.client.MidasClient("SciFiScripts_LvPower")
    try:
        det = detector.SciFiDetector(client)
        if not det.febs:
            seq.msg("No active SciFi (Fibre-type) FEBs found in LinksFibre - nothing to power", is_error=True)
            return

        action = "on" if power_on else "off"
        done, skipped = det.turn_on_all_lv() if power_on else det.turn_off_all_lv()
        total = len([f for f in det.febs.values() if f.has_lv_supply()])
        seq.msg(f"LV power {action}: {len(done)}/{total} Feb(s) switched ({done})")
        if skipped:
            seq.msg(f"Skipped {len(skipped)} Feb(s): {skipped}", is_error=True)

        if power_on and done:
            seq.msg(f"Waiting {settle_seconds}s for current to settle before checking...")
            seq.wait_seconds(settle_seconds)
            offenders = []
            for feb_index in done:
                ok, message = det.febs[feb_index].check_lv_status(expected_current_a, current_tolerance_a)
                if not ok:
                    offenders.append(f"Feb {feb_index}: {message}")
            if offenders:
                seq.msg(
                    f"{len(offenders)}/{len(done)} Feb(s) have Current outside "
                    f"{expected_current_a}+/-{current_tolerance_a}A (UNVERIFIED threshold - "
                    f"could be normal ramp-up, or just a wrong assumption): {offenders}",
                    is_error=True,
                )
    finally:
        client.disconnect()
