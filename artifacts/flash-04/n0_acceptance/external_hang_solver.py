#!/usr/bin/env python3
"""Pathological external solver: never answers.

Used as a null control for the process-boundary timeout.  The harness must FAIL
this solver (SolverTimeout) rather than hang (HANDOFF.md section 6).
"""
import time

if __name__ == "__main__":
    time.sleep(3600)
