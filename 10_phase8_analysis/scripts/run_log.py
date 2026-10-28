"""Run log in the format of the analysis chain: script, mode, run time, Python version and MD5 of inputs and outputs.

Written to 10_phase8_analysis/results/logs/<script stem>_<date-time>.json. Used by scripts 30 to 36 (2026-10-27).
"""
import datetime, hashlib, json, os, platform

LOGS = "10_phase8_analysis/results/logs"

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def write(script, inputs, outputs, mode="FINAL", **extra):
    """inputs and outputs: lists of paths (relative to the project root)."""
    os.makedirs(LOGS, exist_ok=True)
    now = datetime.datetime.now().astimezone()
    log = {"script": os.path.basename(script), "mode": mode, "run_time": now.isoformat(timespec="seconds"),
           "python": platform.python_version(),
           "inputs": {p: md5(p) for p in inputs if os.path.isfile(p)},
           "outputs": {p: md5(p) for p in outputs if os.path.isfile(p)}}
    log.update(extra)
    path = os.path.join(LOGS, f"{os.path.splitext(os.path.basename(script))[0]}_{now.strftime('%Y-%m-%dT%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    return path
