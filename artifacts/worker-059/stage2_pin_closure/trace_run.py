#!/usr/bin/env python3
"""Deterministic file-access tracer for a target python entry point.

usage: python3 trace_run.py ROOT TRACE_OUT TARGET [ARGS...]

Runs TARGET in-process with runpy under an audit hook that records every
opened path and every executed code object filename. Writes a JSON list of
absolute paths (sorted) to TRACE_OUT. Exit code mirrors TARGET's exit code.

No timestamps, no environment capture: two runs on the same inputs produce the
same TRACE_OUT list.
"""
from __future__ import annotations

import json
import os
import runpy
import sys

TOOL = os.path.abspath(__file__)


def main() -> int:
    root = os.path.abspath(sys.argv[1])
    trace_out = os.path.abspath(sys.argv[2])
    target = os.path.abspath(sys.argv[3])
    target_args = sys.argv[4:]

    seen: set[str] = set()

    def hook(event: str, eargs: tuple) -> None:
        try:
            if event == "open":
                p = eargs[0]
                if isinstance(p, (str, bytes, os.PathLike)):
                    seen.add(os.path.abspath(os.fsdecode(p)))
            elif event == "exec":
                code = eargs[0]
                fname = getattr(code, "co_filename", None)
                if fname:
                    seen.add(os.path.abspath(str(fname)))
        except Exception:  # audit hooks must never raise
            pass

    sys.addaudithook(hook)
    sys.argv = [target, *target_args]
    rc = 0
    try:
        runpy.run_path(target, run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        rc = code if isinstance(code, int) else (0 if code is None else 1)
    except BaseException as exc:  # report, do not swallow silently
        print(f"trace_run: target raised {type(exc).__name__}: {exc}", file=sys.stderr)
        rc = 70

    rel = sorted(
        p
        for p in seen
        if p.startswith(root + os.sep)
        and p not in (trace_out, TOOL)
        and not p.startswith(os.path.join(root, "artifacts", "worker-059", "stage2_pin_closure", "work") + os.sep)
    )
    with open(trace_out, "w", encoding="utf-8") as fh:
        json.dump(rel, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
