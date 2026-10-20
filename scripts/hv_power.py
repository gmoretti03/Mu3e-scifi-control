"""
PySequencer entry point: SciFi SiPM-bias HV on/off, on the new
scifi_scripts object model - replaces the original bulk hv_power.py.
/Equipment/HV has no Labor/Fibre split (single tree, shared by the whole
detector) and no Labor copy at all - only ever exercised for real on
mu3ebe.

HV is a flat, independent set of channels here (detector/hv.py's ScifiHv),
deliberately NOT owned by any Feb - the channel<->SMB order isn't
documented anywhere, even though the total count (24) is confirmed 1:1
with SMB by design. This script pattern-matches "SciFi CH" in Names[]
and acts on every match at once, exactly like the original script.
"""

import midas.client
import common.setup as setup
import detector.scifi as detector
import detector.hv as hv

DEFAULT_DEMAND_VOLTAGE = 56.0
DEFAULT_HV_EXPECTED_CURRENT_UA = 1.5  # UNVERIFIED, see module docstring
DEFAULT_HV_CURRENT_TOLERANCE_UA = 1.0


def define_params(seq):
    seq.register_param("power_on", "True = enable HV output, False = disable", True)
    seq.register_param(
        "demand_voltage",
        f"Target voltage when powering on (default {DEFAULT_DEMAND_VOLTAGE}V, hard max "
        f"{hv.ScifiHv.MAX_DEMAND_VOLTAGE}V) - ignored if power_on=False",
        DEFAULT_DEMAND_VOLTAGE,
    )
    seq.register_param(
        "settle_seconds",
        "Wait this long after powering on before checking Current (real ramp/settle time unverified - adjust as needed)",
        10,
    )
    seq.register_param(
        "expected_current_ua",
        f"Expected Current per channel in uA once settled (UNVERIFIED default {DEFAULT_HV_EXPECTED_CURRENT_UA}uA, "
        "adjust once real values are known)",
        DEFAULT_HV_EXPECTED_CURRENT_UA,
    )
    seq.register_param(
        "current_tolerance_ua",
        f"+/- tolerance around expected_current_ua before flagging a channel (UNVERIFIED default {DEFAULT_HV_CURRENT_TOLERANCE_UA}uA)",
        DEFAULT_HV_CURRENT_TOLERANCE_UA,
    )
    seq.register_param("is_odb_available", "Is there a real, correct ODB on this machine", True)
    seq.register_param("can_send_commands_to_odb", "Actually write to ODB (False = dry run)", True)


def sequence(seq):
    power_on = seq.get_param("power_on")
    demand_voltage = seq.get_param("demand_voltage")
    settle_seconds = seq.get_param("settle_seconds")
    expected_current_ua = seq.get_param("expected_current_ua")
    current_tolerance_ua = seq.get_param("current_tolerance_ua")
    setup.is_odb_available = seq.get_param("is_odb_available")
    setup.can_send_commands_to_odb = seq.get_param("can_send_commands_to_odb")

    # Own MidasClient, always disconnected via try/finally - see
    # scripts/feb_power.py's module docstring for why.
    client = midas.client.MidasClient("SciFiScripts_HvPower")
    try:
        det = detector.SciFiDetector(client)
        if not det.hv.get_channel_indices():
            seq.msg(f"No channel names containing '{det.hv.NAME_PATTERN}' found in HV/Settings/Names - nothing to power", is_error=True)
            return

        if power_on:
            pd_ok, pd_message = det.hv.check_power_distribution()
            if not pd_ok:
                seq.msg(f"Power distribution not healthy, refusing to power on: {pd_message}", is_error=True)
                return

        action = "on" if power_on else "off"
        done, skipped = det.hv.turn_on(demand_voltage) if power_on else det.hv.turn_off()
        total = len(det.hv.get_channel_indices())
        named_done = [(i, det.hv.get_name(i)) for i in done]
        seq.msg(f"HV power {action}: {len(done)}/{total} channel(s) switched ({named_done})")
        if skipped:
            named_skipped = {i: (det.hv.get_name(i), reason) for i, reason in skipped.items()}
            seq.msg(f"Skipped {len(skipped)} channel(s): {named_skipped}", is_error=True)

        if power_on and done:
            seq.msg(f"Waiting {settle_seconds}s for HV to ramp/settle before checking...")
            seq.wait_seconds(settle_seconds)
            offenders = []
            for index in done:
                ok, message = det.hv.check_status(index, expected_current_ua, current_tolerance_ua)
                if not ok:
                    offenders.append(f"{index} ({det.hv.get_name(index)}): {message}")
            if offenders:
                seq.msg(
                    f"{len(offenders)}/{len(done)} channel(s) have Current outside "
                    f"{expected_current_ua}+/-{current_tolerance_ua}uA (UNVERIFIED threshold, "
                    f"and HV is still ramping - could easily be premature, not a real fault): {offenders}",
                    is_error=True,
                )
    finally:
        client.disconnect()
