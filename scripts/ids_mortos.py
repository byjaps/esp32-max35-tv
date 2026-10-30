"""Finds globals/ids defined in the panel YAML that are never used.

Usage: python3 ids_mortos.py [path/to/esp32-max35-tv.yaml]
"""
import re
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "esp32-max35-tv.yaml"
src = open(P, encoding="utf-8").read()

# globals: block
i = src.index("\nglobals:\n")
j = src.index("\nscript:\n", i)
bloco = src[i:j]

ids = re.findall(r"^  - id: (\w+)", bloco, re.M)
print(f"globals defined: {len(ids)}")
mortos = []
for nome in ids:
    # count references outside the definition
    total = len(re.findall(rf"\b{re.escape(nome)}\b", src))
    if total <= 1:
        mortos.append(nome)
print("unused:", mortos if mortos else "(none)")

# also scripts that are defined and never called
i2 = src.index("\nscript:\n")
ids2 = re.findall(r"^  - id: (\w+)", src[i2:], re.M)
mortos2 = []
for nome in ids2:
    if len(re.findall(rf"\b{re.escape(nome)}\b", src)) <= 1:
        mortos2.append(nome)
print(f"scripts defined: {len(ids2)} | unused:", mortos2 if mortos2 else "(none)")
