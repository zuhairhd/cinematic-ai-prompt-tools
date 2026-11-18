"""Deterministic timecode calculation.

The AI may suggest relative pacing (one weight per beat) but Python owns the final timeline:
  * exactly 9 beats, first starts at 0, last ends at the selected duration
  * contiguous (no gaps, no overlaps), every beat strictly positive
  * cut points snap to a display quantum (0.5 s, or 0.1 s for very short clips) and are
    repaired so rounding can never produce a zero-length or reversed interval.
"""

from .constants import BEAT_WEIGHTS, MIN_DURATION, MAX_DURATION

N_BEATS = 9
WEIGHT_MIN, WEIGHT_MAX = 0.3, 4.0


class TimingError(ValueError):
    pass


def quantum_for(duration):
    """0.5 s steps like the lesson, unless the clip is too short to give 9 beats >= 0.5 s."""
    return 0.5 if duration >= N_BEATS * 0.5 else 0.1


def fmt_time(t, quantum=0.5):
    """Format seconds as the lesson does: 0:00, 0:01.5, 0:12.5, 1:05 (0.1 s precision if quantum < 0.5)."""
    t = round(t / quantum) * quantum
    tenths = int(round(t * 10))
    m, rem = divmod(tenths, 600)
    s, d = divmod(rem, 10)
    return f"{m}:{s:02d}" + (f".{d}" if d else "")


def check_duration(duration):
    try:
        f = float(str(duration).strip())
    except (TypeError, ValueError):
        f = None
    if isinstance(duration, bool) or f is None or not f.is_integer():
        raise TimingError(f"Duration must be a whole number of seconds, got {duration!r}.")
    d = int(f)
    if not MIN_DURATION <= d <= MAX_DURATION:
        raise TimingError(f"Duration must be between {MIN_DURATION} and {MAX_DURATION} seconds (got {d}).")
    return d


def normalize_weights(weights):
    """Return 9 usable weights; None -> lesson weights. Values are clamped to a sane ratio range."""
    if weights is None:
        return list(BEAT_WEIGHTS)
    weights = list(weights)
    if len(weights) != N_BEATS:
        raise TimingError(f"Expected {N_BEATS} beat weights, got {len(weights)}.")
    out = []
    for i, w in enumerate(weights, 1):
        if isinstance(w, bool) or not isinstance(w, (int, float)) or w != w or w <= 0:
            raise TimingError(f"Beat {i} has an invalid pacing weight: {w!r}.")
        out.append(min(max(float(w), WEIGHT_MIN), WEIGHT_MAX))
    return out


def compute_cut_units(duration, weights=None):
    """Integer cut points (in quanta). Mirrors the original scaling so legacy timecodes are unchanged."""
    duration = check_duration(duration)
    weights = normalize_weights(weights)
    q = quantum_for(duration)
    units = int(round(duration / q))
    total = sum(weights)
    cuts, acc = [0], 0.0
    for w in weights[:-1]:
        acc += w * duration / total
        cuts.append(int(round(acc / q)))
    cuts.append(units)
    # Repair: every beat must last at least one quantum (forward, then backward from the end).
    for i in range(1, N_BEATS):
        cuts[i] = max(cuts[i], cuts[i - 1] + 1)
    for i in range(N_BEATS - 1, 0, -1):
        cuts[i] = min(cuts[i], cuts[i + 1] - 1)
    return cuts, q


def compute_timeline(duration, weights=None):
    """List of 9 dicts: {panel, start, end, length, timecode}."""
    cuts, q = compute_cut_units(duration, weights)
    tl = []
    for i in range(N_BEATS):
        start, end = round(cuts[i] * q, 3), round(cuts[i + 1] * q, 3)
        tl.append({"panel": i + 1, "start": start, "end": end, "length": round(end - start, 3),
                   "timecode": f"{fmt_time(start, q)}–{fmt_time(end, q)}"})
    return tl


def compute_timecodes(duration, weights=None):
    return [b["timecode"] for b in compute_timeline(duration, weights)]


def validate_timeline(timeline, duration):
    """Deterministic timing checks. Returns a list of error strings (empty = valid)."""
    errs = []
    if len(timeline) != N_BEATS:
        return [f"Timeline has {len(timeline)} scenes; exactly {N_BEATS} are required."]
    if abs(timeline[0]["start"]) > 1e-9:
        errs.append(f"First scene starts at {timeline[0]['start']} s instead of 0.")
    for i, b in enumerate(timeline):
        if b["end"] - b["start"] <= 1e-9:
            errs.append(f"Scene {i + 1} has non-positive duration ({b['start']}–{b['end']}).")
        if i and abs(b["start"] - timeline[i - 1]["end"]) > 1e-9:
            kind = "gap" if b["start"] > timeline[i - 1]["end"] else "overlap"
            errs.append(f"Timing {kind} between scenes {i} and {i + 1}.")
        a, _, z = b["timecode"].partition("–")
        if a == z:
            errs.append(f"Scene {i + 1} displays a zero-length timecode ({b['timecode']}).")
    if abs(timeline[-1]["end"] - float(duration)) > 1e-9:
        errs.append(f"Last scene ends at {timeline[-1]['end']} s instead of {duration} s.")
    return errs
