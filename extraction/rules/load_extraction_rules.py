import json
import os


path_to_import = os.path.join(os.path.dirname(__file__), "extraction_rules.json")

RULES = {}

with open(path_to_import, "r") as f:
    rules = json.load(f)
    for key in rules:
        if key not in RULES:
            RULES[key] = rules[key]
        else:
            raise KeyError(f"Duplicate key found in {path_to_import}: {key}")