"""Quick test: download WordPress and scan (no Gemini needed)."""
from repo_analyzer import clone_repo, scan_repo
from pathlib import Path
from collections import Counter

d = Path(".repos/WordPress")
clone_repo("https://github.com/WordPress/WordPress", d, depth=1)
s = scan_repo(d)
print(f"\nFiles: {s['total_files']}")
print(f"README: {len(s['readme'])} chars")
print(f"Configs: {len(s['config_files'])}")
print(f"Source files sampled: {len(s['key_source_files'])}")
print(f"\nTop directories:")
dirs = Counter(f.split("/")[0] if "/" in f else f for f in s["file_tree"])
for d2, c in dirs.most_common(15):
    print(f"  {d2}: {c} files")
print("\nConfig files found:")
for cf in s["config_files"][:5]:
    print(f"  {cf['path']}")
print("\n✅ WordPress repo scanned - ready for Gemini DPR generation")
