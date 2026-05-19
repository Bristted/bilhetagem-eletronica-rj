"""
Baixa recursos do dataset SETRAM SBE (dados abertos RJ).

Inclui:
  - Consolidados mensais 2025 (jan a mai)
  - Transações diárias públicas (1 semana em maio/2025)
  - Dicionário de dados (XLSX)

Uso:
  python baixar_dados_reais.py
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
DADOS_DIR = BASE_DIR / "dados"
DIR_CONSOLIDADO = DADOS_DIR / "consolidado"
DIR_PUBLICO = DADOS_DIR / "publico"
DIR_DOCS = DADOS_DIR / "documentacao"
CKAN_API = "https://dadosabertos.rj.gov.br/api/3/action/package_show?id=setram_sbe"

# Dias da semana de amostra (maio/2025) — arquivos diários
DIAS_PUBLICO = [f"2025_05_{d:02d}" for d in range(1, 8)]
MESES_CONSOLIDADO = ["01", "02", "03", "04", "05"]


def _get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (projeto-academico)"})
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def listar_recursos() -> list[dict]:
    pkg = _get_json(CKAN_API)
    if not pkg.get("success"):
        raise RuntimeError("Falha na API CKAN do portal RJ")
    return pkg["result"]["resources"]


def csv_consolidado_existe(mes: str) -> bool:
    padrao = f"*2025_{mes}.csv"
    return any(DIR_CONSOLIDADO.glob(padrao)) or any(DADOS_DIR.glob(padrao))


def baixar_arquivo(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.is_file() and destino.stat().st_size > 50_000:
        print(f"  [ok] já existe: {destino.name}")
        return
    print(f"  baixando: {destino.name}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=600) as resp:
        destino.write_bytes(resp.read())
    mb = destino.stat().st_size / 1_048_576
    print(f"  salvo ({mb:.2f} MB): {destino}")


def extrair_zip(zip_path: Path, destino: Path) -> None:
    if zip_path.stat().st_size < 50_000:
        print(f"  [aviso] ZIP inválido/pequeno — ignorando extração: {zip_path.name}")
        zip_path.unlink(missing_ok=True)
        return
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destino)


def recurso_consolidado(recursos: list[dict], mes: str) -> dict | None:
    padrao = re.compile(rf"consolidadobe_2025_{mes}\.csv", re.I)
    for r in recursos:
        nome = (r.get("name") or "") + " " + (r.get("url") or "")
        if padrao.search(nome):
            return r
    return None


def recurso_publico(recursos: list[dict], dia: str) -> dict | None:
    padrao = re.compile(rf"transacao_be_publico_{dia}\.csv", re.I)
    for r in recursos:
        nome = (r.get("name") or "") + " " + (r.get("url") or "")
        if padrao.search(nome):
            return r
    return None


def recurso_dicionario(recursos: list[dict]) -> dict | None:
    for r in recursos:
        nome = (r.get("name") or "").lower()
        fmt = (r.get("format") or "").lower()
        if "dicionario" in nome and ("xlsx" in nome or "xls" in nome or fmt in ("xlsx", "xls")):
            return r
    return None


def url_download(rec: dict) -> str:
    """Prefer URL direta de download do CKAN."""
    rid = rec.get("id", "")
    nome = Path(rec.get("url") or "").name
    if rid and nome:
        return (
            f"https://dadosabertos.rj.gov.br/dataset/setram_sbe/resource/{rid}/download/{nome}"
        )
    return rec["url"]


def baixar_consolidados(recursos: list[dict]) -> None:
    print("\n=== Consolidados mensais (jan–mai/2025) ===")
    for mes in MESES_CONSOLIDADO:
        if csv_consolidado_existe(mes):
            print(f"  [ok] CSV do mês {mes} já extraído")
            continue
        rec = recurso_consolidado(recursos, mes)
        if not rec:
            print(f"  [pulado] mês {mes} não encontrado na API")
            continue
        nome_zip = Path(rec.get("url") or "").name or f"transacoesconsolidadobe_2025_{mes}.csv.zip"
        zip_path = DIR_CONSOLIDADO / nome_zip
        baixar_arquivo(url_download(rec), zip_path)
        extrair_zip(zip_path, DIR_CONSOLIDADO)


def baixar_publico(recursos: list[dict]) -> None:
    print("\n=== Transações diárias (amostra: 01–07/mai/2025) ===")
    for dia in DIAS_PUBLICO:
        rec = recurso_publico(recursos, dia)
        if not rec:
            print(f"  [pulado] {dia} não encontrado")
            continue
        nome_zip = Path(rec["url"]).name
        zip_path = DIR_PUBLICO / nome_zip
        baixar_arquivo(url_download(rec), zip_path)
        extrair_zip(zip_path, DIR_PUBLICO)


def baixar_dicionario(recursos: list[dict]) -> None:
    print("\n=== Dicionário de dados ===")
    rec = recurso_dicionario(recursos)
    if not rec:
        print("  [pulado] dicionário não encontrado")
        return
    nome = Path(rec["url"]).name
    baixar_arquivo(url_download(rec), DIR_DOCS / nome)


def main() -> None:
    for d in (DIR_CONSOLIDADO, DIR_PUBLICO, DIR_DOCS):
        d.mkdir(parents=True, exist_ok=True)
    print("Consultando API CKAN...")
    recursos = listar_recursos()
    print(f"Recursos no dataset: {len(recursos)}")
    baixar_consolidados(recursos)
    baixar_publico(recursos)
    baixar_dicionario(recursos)
    print("\nDownload finalizado.")
    print("Próximo passo: python analise_bilhetagem_rj.py")


if __name__ == "__main__":
    main()
