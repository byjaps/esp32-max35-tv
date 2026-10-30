"""Encontra globais/ids definidos no YAML do painel que nunca são usados.

Uso: python3 ids_mortos.py [caminho/para/esp32-max35-tv.yaml]
"""
import re
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "esp32-max35-tv.yaml"
src = open(P, encoding="utf-8").read()

# bloco globals:
i = src.index("\nglobals:\n")
j = src.index("\nscript:\n", i)
bloco = src[i:j]

ids = re.findall(r"^  - id: (\w+)", bloco, re.M)
print(f"globais definidos: {len(ids)}")
mortos = []
for nome in ids:
    # conta referências fora da definição
    total = len(re.findall(rf"\b{re.escape(nome)}\b", src))
    if total <= 1:
        mortos.append(nome)
print("sem uso:", mortos if mortos else "(nenhum)")

# também scripts definidos e nunca chamados
i2 = src.index("\nscript:\n")
ids2 = re.findall(r"^  - id: (\w+)", src[i2:], re.M)
mortos2 = []
for nome in ids2:
    if len(re.findall(rf"\b{re.escape(nome)}\b", src)) <= 1:
        mortos2.append(nome)
print(f"scripts definidos: {len(ids2)} | sem uso:", mortos2 if mortos2 else "(nenhum)")
