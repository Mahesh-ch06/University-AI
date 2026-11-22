import json
import re

with open("backend/app/sru_agent/fees_2027_28.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== 1. CHECKING OVERLAPPING ALIASES IN fees_2027_28.json ===")
alias_map = {}
for p_key, p_val in data["programs"].items():
    for alias in p_val.get("aliases", []):
        alias_clean = alias.strip().lower()
        if alias_clean in alias_map:
            alias_map[alias_clean].append((p_key, p_val["name"]))
        else:
            alias_map[alias_clean] = [(p_key, p_val["name"])]

overlap = {k: v for k, v in alias_map.items() if len(v) > 1}
print(f"Overlapping aliases: {len(overlap)}")
for k, v in overlap.items():
    print(f"  Alias '{k}': {v}")

print("\n=== 2. CHECKING KEYWORD / SPECIALIZATION DUPLICATES ===")
# Check which specialization keywords appear in multiple program names
keywords = ["robotics", "ai", "aiml", "data science", "cyber security", "vlsi", "smart manufacturing", "quantum"]
for kw in keywords:
    matches = []
    for p_key, p_val in data["programs"].items():
        name = p_val["name"]
        aliases = p_val.get("aliases", [])
        if kw in name.lower() or any(kw in a.lower() for a in aliases):
            matches.append((p_key, name, p_val["tuition_per_year"]))
    if len(matches) > 1:
        print(f"Keyword '{kw}' matches {len(matches)} programs:")
        for m in matches:
            print(f"    - {m[0]}: {m[1]} -> Rs {m[2]:,}")

print("\n=== 3. CHECKING FEE CARD PDF ROWS VS fees_2027_28.json ===")
# Check if any program in the official fee card is missing or misnamed
for p_key, p_val in data["programs"].items():
    print(f"Program [{p_key}]: {p_val['name']}")
    print(f"    Tuition: Rs {p_val['tuition_per_year']:,} | Yearly Increase: Rs {p_val['yearly_increase']:,}")
    if "specialization_fee_per_year_from_year2" in p_val:
        print(f"    Spec fee from yr 2: Rs {p_val['specialization_fee_per_year_from_year2']:,}")
