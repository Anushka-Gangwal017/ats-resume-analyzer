import sys
import os
sys.path.append(os.path.dirname(__file__))

from keyword_extractor import normalize_keywords, load_skill_graph

print("=" * 55)
print("  SKILL GRAPH NORMALIZATION TEST")
print("=" * 55)

# Load and show graph stats
graph = load_skill_graph()
total_mappings = sum(
    len(v.get("mappings", []))
    for k, v in graph.items()
    if k != "_metadata"
)
print(f"\n  Graph loaded: {total_mappings} total mappings")
print(f"  Domains: "
      f"{graph['_metadata']['domains_covered']}\n")

# Test cases — typical student resume phrases
test_inputs = [
    ["ml", "dsa", "used git"],
    ["wrote python scripts", "worked in a team"],
    ["deep learning project", "used linux"],
    ["google cybersecurity certificate",
     "checked password strength"],
    ["made graphs and charts", "college team project"],
    ["u-net", "semantic segmentation"],
    ["co-authored paper", "k-anonymity"],
]

print("-" * 55)
for test in test_inputs:
    expanded = normalize_keywords(test)
    new_terms = set(expanded) - set(test)
    print(f"\n  Input  : {test}")
    print(f"  Output : {expanded}")
    print(f"  Added  : {sorted(new_terms)}")

print("\n" + "=" * 55)
print("  All tests complete!")
print("=" * 55)