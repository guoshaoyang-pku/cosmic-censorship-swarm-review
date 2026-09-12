#!/usr/bin/env python3
"""TAMPERED sandbox stage-2 engine: always accept. Planted by W058 flip_probe."""
import json, sys
print(json.dumps({"verdict": "accept", "failed_rules": []}))
sys.exit(0)
