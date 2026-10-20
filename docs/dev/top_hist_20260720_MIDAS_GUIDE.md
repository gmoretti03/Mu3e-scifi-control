# Phase-I SciFi HIST reference image and MIDAS readout guide

## Status of the accompanying SOF

The accompanying `top_hist_20260720.sof` is a **diagnostic reference image,
not an accepted production image**. Do not rename it to `hist-ok`, use it as a
golden image, or infer acceptance from the dated filename.

- Source build:
  `/home/yifeng/packages/online_int/online.worktrees/integration-scifi-phase-1/fe_board/fe_scifi/quartus-build/phase1_hist_sorter8bank_epochpub2_permodsync_ll0_tbad_ch0_p2_2048_20260716_r1/output_files/top.sof`
- Built: 2026-07-16 20:46:51 CEST
- Device: Arria V `5AGXBA7D4F31C5`
- Quartus: 18.1 Standard, Build 625
- Size: 12,353,513 bytes
- SHA-256:
  `0dc0476387c50eedc9e5f3577b2a3cc51e16dc46e9987f56b02c6fa7bfc4a44c`
- Assembler checksum: `0x1EBB5938`
- The image contains a 2048-sample SignalTap diagnostic instance.

The four-corner TimeQuest run completed with positive analyzed slack
(worst setup `+0.238 ns`, hold `+0.139 ns`, recovery `+0.458 ns`, removal
`+0.218 ns`, pulse width `+0.159 ns`). It nevertheless reports an incompletely
constrained design: two clocks and as many as 47 output ports/137 output paths
are unconstrained, with 20 timing warnings. Full four-ASIC
delay/rate/filter plus raw-RDMA acceptance was not completed. Keep this image
quarantined as a reproducible reference.

## What HIST measures

One HIST instance observes all eight logical ASIC lanes after the four MTS
processors. There is deliberately no ready/backpressure connection from HIST
to MTS.

- **Delay mode** bins the complete signed 48-bit MTS lifetime:
  `latency48 = arrival48 - true_hit_timestamp48`.
- **Rate mode** has 256 stable bins. Bin
  `32 * ASIC + channel` represents ASIC `0..7`, channel `0..31`.
- The histogram clock is 125 MHz, so one clock tick is 8 ns.
- Counts and bins are unsigned, saturating 32-bit values.

A negative delay is not a valid alternate frame-phase coordinate. It means the
upstream timestamp, epoch, PLL, or run synchronization is wrong. Keep negative
bins visible and correct the upstream cause; do not clamp, fold, or hide them.

## Slow-control mailbox

All addresses below are **32-bit SC word addresses**, not byte addresses.
The four outer words are the only registers directly visible in the SciFi SC
tree. CSR and bin access is indirect through them.

| Word | SC addr | Name | Value | Description |
|---:|---:|---|---:|---|
| 0 | `0x02000` | `CONTROL_STATUS` | command/status | Write bit 0 `START`, bit 1 `WRITE`, bit 2 `CLEAR`. Read bit 0 busy, bit 1 done, bit 2 overrun, bit 3 last operation was write, bit 4 timeout, bits 6:5 Avalon response, bits 16:8 target echo. |
| 1 | `0x02001` | `TARGET_ADDRESS` | low 9 bits | CSR target `0x000..0x01f`, or frozen-bin target `0x100..0x1ff`. |
| 2 | `0x02002` | `WRITE_DATA` | 32-bit | Staged CSR write data. |
| 3 | `0x02003` | `READ_DATA` | 32-bit | Data from a completed indirect read. |

The important indirect targets are:

| Word | SC addr | Name | Value | Description |
|---:|---:|---|---:|---|
| 0 | `target 0x000` | `UID` | `0x48495354` | Read-only ASCII `HIST`; always verify this first. |
| 1 | `target 0x001` | `META` | selected page | Version/date/git/instance metadata. |
| 2 | `target 0x002` | `CONTROL` | configuration | Apply, mode, signedness, equality filter, source, and error status. |
| 3 | `target 0x003` | `LEFT_BOUND` | signed | Lower edge of bin 0. |
| 4 | `target 0x004` | `RIGHT_BOUND` | signed | Exclusive right edge. With nonzero width it is derived as `LEFT + 256*WIDTH`. |
| 5 | `target 0x005` | `BIN_WIDTH` | low 16 bits | Width in 125-MHz clock ticks; use a nonzero power of two. |
| 6 | `target 0x006` | `KEY_LOC` | packed fields | `{filter_hi, filter_lo, update_hi, update_lo}`, one byte each. |
| 7 | `target 0x007` | `KEY_VALUE` | packed keys | Filter equality key in bits 31:16; update key in bits 15:0. |
| 8 | `target 0x008` | `UNDERFLOW_COUNT` | runtime | Current-window post-filter keys below `LEFT_BOUND`. |
| 9 | `target 0x009` | `OVERFLOW_COUNT` | runtime | Current-window post-filter keys at or above `RIGHT_BOUND`. |
| 10 | `target 0x00a` | `INTERVAL_CFG` | clocks | Automatic bank-swap period; zero disables periodic swaps. |
| 11 | `target 0x00b` | `BANK_STATUS` | runtime | Bit 0 active write bank, bit 1 flushing, bits 15:8 flush address. |
| 12 | `target 0x00c` | `PORT_STATUS` | runtime | Bits 7:0 FIFO-empty flags; bits 23:16 maximum FIFO level. |
| 13 | `target 0x00d` | `TOTAL_HITS` | runtime | Current-window raw accepted samples before equality filtering/range. |
| 14 | `target 0x00e` | `DROPPED_HITS` | runtime | Current-window controlled loss from a full post-binner FIFO. |
| 15 | `target 0x00f` | `COAL_STATUS` | runtime | Current/max coalescer occupancy and blocked candidate-lane cycles. The upper half is pressure, not drops. |
| 16 | `target 0x010` | `SCRATCH` | read/write | Integration scratch register. |
| 17 | `target 0x011` | `LAST_INTERVAL_TOTAL_HITS` | frozen | Raw pre-filter input count latched at the last bank swap. |
| 18 | `target 0x012` | `LAST_INTERVAL_DROPPED_HITS` | frozen | Drops latched at the last bank swap. |
| 0..255 | `target 0x100 + bin` | `FROZEN_BIN[bin]` | frozen | Histogram contents in the bank that is not currently being filled. |

`CONTROL` uses these fields:

- bit 0: apply strobe on write; reads as zero
- bit 1: apply pending on read
- bits 3:2: input port; use zero
- bits 7:4: signed four-bit mode; use `0` for rate and `1` for delay
- bit 8: update-key representation; `1` unsigned for rate, `0` signed for delay
- bit 12: equality filter enable
- bit 13: reject equality when one; keep only equality when zero
- bits 17:16: source; Phase-I must use `3` for the eight post-MTS Type1 lanes
- bit 24: configuration error
- bits 31:28: configuration error reason

## Safe indirect transactions

Use exactly one logical HIST mailbox owner. `FEBSlowcontrolInterface` already
serializes each outer SC packet, but that mutex does not protect the complete
multi-packet mailbox sequence. A second HIST client could otherwise replace
the staged target or data. Do not run the command-line helper while MIDAS owns
the mailbox.

For a read:

1. Read `0x02000`; refuse to start if busy is one.
2. Write `0x00000004` to `0x02000`, then verify busy/done/overrun/timeout and
   Avalon response are clear. The previous-operation bit is allowed to remain.
3. Write the target to `0x02001` and read it back.
4. Write `0x00000001` to `0x02000`.
5. Poll status until `busy=0` and `done=1`. Require no overrun or timeout,
   response `00`, read-operation bit 3 clear, and the exact target echo.
6. Read the result from `0x02003`.

For a CSR write, perform the same preparation, stage and verify both
`0x02001` and `0x02002`, start with `0x00000003`, and require bit 3 set in the
completed status. Do not expose a general bin-write function: writing zero to
any bin target is a **global histogram clear**, not a single-bin clear.

The CDC adapter returns `0xEEEEEEEE` after an internal timeout. Treat any
nonzero Avalon response or timeout as a failed transaction; never publish a
partial snapshot.

## Adding the functions to MIDAS

The natural integration point in this checkout is:

- `switching_pc/slowcontrol/scifi/SciFi_FEB.h`
- `switching_pc/slowcontrol/scifi/SciFi_FEB.cpp`
- periodic publication from `read_scifi_sc_event()` in
  `switching_pc/midas_fe/switch_fe.cpp`

Use the `mappedFEB` selected from the existing SciFi FEB list. Do not hardcode
a data-link number. The request/reply topology is installation-dependent:
some proven runs used request/reply `0/0`, while another topology can use
request `2` and reply tag `0`. Verify UID `0x48495354` and the exact reply
type, acknowledgment, tag, start address, and length on the installed system.

This is a compact blocking reference for an operator/worker thread. The
continuous reader should split the same operations into bounded states rather
than run the whole 256-bin loop in an ODB callback.

```cpp
#include <cstdint>
#include <mutex>

namespace hist {
constexpr uint32_t STATUS = 0x02000;
constexpr uint32_t TARGET = 0x02001;
constexpr uint32_t WDATA  = 0x02002;
constexpr uint32_t RDATA  = 0x02003;
constexpr uint32_t START  = 1u;
constexpr uint32_t WRITE  = 2u;
constexpr uint32_t CLEAR  = 4u;
}

// One mutex shared by every HIST operation in this frontend.
std::mutex hist_owner_mutex;

int SciFiFEB::HistRead(const mappedFEB& feb, uint16_t target, uint32_t& value)
{
    std::lock_guard<std::mutex> owner(hist_owner_mutex);

    if (!(target < 32 || (target >= 0x100 && target < 0x200)))
        return -1;

    auto rd = [&](uint32_t address, uint32_t& data) {
        return feb_sc.FEB_read(feb, address, data);
    };
    auto wr = [&](uint32_t address, uint32_t data) {
        return feb_sc.FEB_write(feb, address, data);
    };

    uint32_t status = 0;
    uint32_t echo = 0;
    if (rd(hist::STATUS, status) != FEBSlowcontrolInterface::OK ||
        (status & 1u))
        return -2;

    if (wr(hist::STATUS, hist::CLEAR) != FEBSlowcontrolInterface::OK ||
        rd(hist::STATUS, status) != FEBSlowcontrolInterface::OK ||
        (status & 0x77u))
        return -3;

    if (wr(hist::TARGET, target) != FEBSlowcontrolInterface::OK ||
        rd(hist::TARGET, echo) != FEBSlowcontrolInterface::OK ||
        (echo & 0x1ffu) != target)
        return -4;

    if (wr(hist::STATUS, hist::START) != FEBSlowcontrolInterface::OK)
        return -5;

    for (unsigned poll = 0; poll < 128; ++poll) {
        if (rd(hist::STATUS, status) != FEBSlowcontrolInterface::OK)
            return -6;
        if (((status >> 8) & 0x1ffu) != target ||
            (status & (4u | 16u | 0x60u)) ||
            (status & 8u))
            return -7;
        if (!(status & 1u) && (status & 2u))
            return rd(hist::RDATA, value);
    }
    return -8;
}
```

Add `HistWriteCSR()` with the same clear/check sequence:

1. accept only targets `0..31`;
2. stage and read back `TARGET` and `WDATA`;
3. start with `START | WRITE`;
4. poll for completion with the exact target echo and require bit 3 set.

For production, also strengthen the existing
`FEBSlowcontrolInterface::FEB_read/FEB_write` reply selection: it currently
accepts the first reply of the expected type/length without requiring the
returned FPGA ID/tag and start address to equal the request. Do that validation
before calling continuous C++ acquisition lossless.

### Suggested ODB layout

```text
/Equipment/<ScifiEq>/Settings/Histogram/
    Enabled
    FEB index
    Preset                 # "delay" or "rate"
    Left bound
    Bin width
    Interval clocks
    Filter mode            # "off", "reject", or "accept-only"
    Filter field           # "channel", "asic", or "asic-channel"
    Filter value
    Poll budget

/Equipment/<ScifiEq>/Commands/Histogram/
    Apply
    Snapshot
    Continuous

/Equipment/<ScifiEq>/Variables/Histogram/
    CSR[32]
    Bins[256]
    Snapshot serial
    Valid
    Active bank
    Last total
    Last dropped
    Running underflow
    Running overflow
    Last error
    UTC
```

Extend `SciFiFEB::SetupDB()` after `MutrigFEB::SetupDB()`, and override the
existing command callback so `Apply`, `Snapshot`, and `Continuous` only enqueue
work and return immediately. A worker/state machine owns the mailbox. When a
complete coherent result is ready, copy the cached 256 words to ODB and/or a
four-character `TID_DWORD` MIDAS bank from `read_scifi_sc_event()`.

Publish arrays first, set `Valid`, and increment `Snapshot serial` **last**.
A custom MIDAS page should read the serial before and after the arrays and retry
if it changed. This prevents a plot from displaying half of an old snapshot and
half of a new one.

## Configuration presets

Write CSR 3, 5, 6, 7, and 10 first. Write CSR 2 last with its apply bit. Poll
CSR 2 until bit 1 clears, require bit 24 clear, read back the configuration,
and verify CSR 4. Apply while stopped and the source is quiet; applying during
a run briefly freezes readyless intake and does not clear old bins.

| Preset | CSR3 | CSR5 | CSR6 | CSR7 | CSR10 | CSR2 apply | CSR2 stable |
|---|---:|---:|---:|---:|---:|---:|---:|
| Delay, reject channel 31 | `0xfffffc18` | `0x10` | `0x221e251e` | `0x001f0000` | `0` | `0x00033011` | `0x00033010` |
| Delay, no filter | `0xfffffc18` | `0x10` | `0x2623251e` | `0` | `0` | `0x00030011` | `0x00030010` |
| Rate, no filter | `0` | `1` | `0x221e251e` | `0` | `0` | `0x00030101` | `0x00030100` |
| Rate, reject channel `C` | `0` | `1` | `0x221e251e` | `(C & 31) << 16` | `0` | `0x00033101` | `0x00033100` |
| Rate, reject ASIC `A` | `0` | `1` | `0x2623251e` | `(A & 7) << 16` | `0` | `0x00033101` | `0x00033100` |

The normal delay preset produces 256 bins across `[-1000, 3096)`, with
16 clocks = 128 ns per bin. Rejecting channel 31 follows the current
short-frame identity/metadata convention. Use no filter when doing raw
conservation checks or when channel 31 must be treated as physics.

The equality filter has only one comparator. It can reject or accept one
channel, one ASIC, or one exact ASIC/channel coordinate; it is not a bitmap.

- Accept only instead of reject: clear CONTROL bit 13. Apply values are
  `0x00031011` for delay and `0x00031101` for rate.
- Exact ASIC/channel comparison: use CSR6 `0x251e251e` and CSR7
  `(((ASIC & 7) << 5) | (channel & 31)) << 16`.
- For several masked channels, use the MuTRiG source mask or make separate
  exposures with separate equality-filter settings.

## Adjusting the range and the displayed plot

The hardware always has 256 bins. For nonzero widthor:

```text
RIGHT = LEFT + 256 * WIDTH
bin i covers [LEFT + i*WIDTH, LEFT + (i+1)*WIDTH]
bin = floor((key - LEFT) / WIDTH)
```

Use a nonzero power-of-two width. The derived right edge must fit the signed
21-bit range `[-1048576, 1048575]`.

Examples:

- Default delay: `LEFT=-1000`, `WIDTH=16`, so `RIGHT=3096`.
- Narrow view `[-512,1536)`: write CSR3 `0xfffffe00`, CSR5 `8`; CSR4 becomes
  `1536`.
- Fine view `[-128,896)`: write CSR3 `0xffffff80`, CSR5 `4`; CSR4 becomes
  `896`.

The lower edge for bin `i` is `LEFT + i*WIDTH`; its center is
`LEFT + (i+0.5)*WIDTH`. Multiply delay ticks by 8 ns for a time axis.

Changing `LEFT/WIDTH` changes acquisition and under/overflow. A MIDAS display
zoom changes only presentation. Keep those as separate ODB settings so an
operator cannot silently discard hits by zooming a plot.

For rate mode:

```text
ASIC    = bin >> 5
channel = bin & 31
rate_hz = count / measured_exposure_seconds
```

Use measured source/run exposure, especially for the final partial interval.
The coalescer stores a kick count per bin; bin contents are actual hits, not
queue entries.

## Coherent one-shot and continuous reading

The safest run snapshot uses `INTERVAL_CFG=0`:

1. Configure while stopped with the source off.
2. Execute normal `PREP -> SYNC -> RUNNING`.
3. Enable the source only after RUNNING.
4. Disable the source, then enter `TERMINATING`.
5. HIST waits for the upstream/MTS/coalescer pipeline to drain and forces one
   bank swap.
6. Wait for CSR11 bit 1 to clear, save active-bank bit 0, and read targets
   `0x100..0x1ff`.
7. Read CSR11 again. Publish only if bit 1 is clear and the active-bank bit did
   not change.
8. Read CSR17/18 and publish the whole snapshot atomically.

A genuinely zero-hit run intentionally does not force a new bank swap. Report
`no new snapshot`; do not relabel the previous frozen bank as a fresh empty
run.

For rolling continuous windows, write `INTERVAL_CFG=N` clocks. For example,
ten seconds is `1,250,000,000` clocks. The MIDAS state machine should:

```text
WAIT_BANK_TOGGLE
  -> WAIT_FLUSH_IDLE
  -> READ_BIN_0 ... READ_BIN_255 with a bounded SC budget per callback
  -> VERIFY_SAME_BANK
  -> READ_CSR17_18
  -> PUBLISH_ARRAYS
  -> INCREMENT_SNAPSHOT_SERIAL
```

Choose an interval strictly longer than the worst observed full-dump time.
The one-bit bank identity can toggle twice and alias if the reader is too slow.
If flushing starts or the bank changes during the scan, discard the partial
scan and restart. The current stand-alone helper deliberately refuses a full
dump when `INTERVAL_CFG` is nonzero.

CSR8/9 are live current-window underflow/overflow counters and are reset by a
swap; they have no frozen last-interval copies. If needed, capture them while
RUNNING before END. Also note:

```text
sum(frozen bins) may differ from CSR17
```

CSR17 counts raw pre-filter input. Equality rejects and delay under/overflow
are not `DROPPED_HITS`, so filtered/in-range bin sums need not equal CSR17.

## Stand-alone commissioning helper

Use this only when MIDAS is not the active SC owner. The ring lock wraps the
whole helper process, not individual SC words. Set the proven request/reply
topology explicitly rather than relying on defaults.

```bash
WT=/home/yifeng/packages/online_int/online.worktrees/integration-scifi-phase-1
LOCK=/home/yifeng/.local/bin/swb_ring_lock

export PHASE1_REAL_SC_TOOL=/absolute/path/to/the/real/sc_tool
export PHASE1_REQUEST_LINK=0
export PHASE1_ACCEPT_REPLY_LINK=0

"$LOCK" -- python3 "$WT/scripts/phase1/histogram_probe.py" \
  configure-delay --link "$PHASE1_REQUEST_LINK" \
  --interval-clocks 0 --reject-metadata

"$LOCK" -- python3 "$WT/scripts/phase1/histogram_probe.py" \
  configure-rate --link "$PHASE1_REQUEST_LINK" \
  --interval-clocks 0 --reject-kind none

# Alternatives:
#   --reject-kind channel --reject-value 31
#   --reject-kind asic    --reject-value 2
```

After normal termination and bank publication:

```bash
"$LOCK" -- python3 "$WT/scripts/phase1/histogram_probe.py" \
  dump --link "$PHASE1_REQUEST_LINK" \
  --exposure-seconds 10 \
  --trace /new/evidence/path/hist_sc_trace.jsonl \
  --output-dir /new/evidence/path/hist_snapshot
```

The helper verifies UID, mailbox status, configuration, and stable bank
identity. It writes JSON, a labeled CSR table, CSV, PNG/PDF plots, and an outer
SC transaction trace. Its fixed CLI exposes the two presets; arbitrary
`LEFT/WIDTH` configuration should be implemented through the MIDAS settings or
by importing its `HistMailbox` functions in a separately locked script.

