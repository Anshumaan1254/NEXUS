"""Fix: rebuild PostgreSQL nexus_data.json from the original Layer 1 data."""
import json, sys, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path("nexus_layer2").resolve()))

from merge_nexus_data import merge_nexus_data

# 1. Check the original layer1 is still PostgreSQL
l1 = json.loads(Path("postgres-analysis/output/nexus_layer1_dprs.json").read_text(encoding="utf-8"))
repo = l1["nexus_layer1_output"]["repository"]
dprs = l1["nexus_layer1_output"]["total_dprs"]
print(f"Layer 1 source: {repo} ({dprs} DPRs)")

if "postgres" in repo.lower():
    print("OK - Layer 1 is still PostgreSQL, rebuilding nexus_data.json...")
    merge_nexus_data()
    print("Done!")
else:
    print(f"WARNING: Layer 1 was overwritten with {repo}")
    print("Checking if we have a backup...")
    # The nexus_data.json was overwritten but nexus_layer1_dprs.json should still be original
    # since repo_analyzer saves to analyses/WordPress/output/ not postgres-analysis/output/

# 2. Verify WordPress stays separate
wp = Path("analyses/WordPress/output/nexus_data.json")
if wp.exists():
    wpd = json.loads(wp.read_text(encoding="utf-8"))
    print(f"WordPress analysis: {wpd['metadata']['total_dprs']} DPRs (separate)")
