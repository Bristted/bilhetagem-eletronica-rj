"""Verifica se Python e as bibliotecas necessárias estão instaladas."""

from __future__ import annotations

import sys

PACOTES = ("pandas", "numpy", "matplotlib", "seaborn", "sklearn", "openpyxl")


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    faltando: list[str] = []
    for nome in PACOTES:
        try:
            __import__(nome)
            print(f"  OK  {nome}")
        except ImportError:
            print(f"  FALTA  {nome}")
            faltando.append(nome)
    if faltando:
        print("\nInstale com: python -m pip install -r requirements.txt")
        return 1
    print("\nAmbiente pronto para rodar o projeto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
