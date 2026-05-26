from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

COL_DATA = "data_referencia"
COL_HORA = "hora_dia"
COL_MODAL = "modal"
COL_QTD = "total_validacoes"
COL_VALOR = "valor_transacao"
COL_VALOR_LINHA = "valor_linha"
COL_SUBSIDIO = "valor_subsidio"
COL_MES_REF = "mes_referencia"

_MES_PARA_NUM = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


def norm_nome(col: str) -> str:
    s = unicodedata.normalize("NFKD", str(col))
    s = s.encode("ascii", "ignore").decode("ascii")
    return s.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")


def achar_coluna(colunas: list[str], candidatos: tuple[str, ...]) -> str | None:
    norm = {norm_nome(c): c for c in colunas}
    for cand in candidatos:
        if cand in norm:
            return norm[cand]
    for cand in candidatos:
        for k, orig in norm.items():
            if k.startswith(cand) or k.endswith(cand) or f"_{cand}_" in f"_{k}_":
                return orig
    return None


def parse_numero_br(valor: object) -> float:
    if pd.isna(valor):
        return float("nan")
    s = str(valor).strip().replace("R$", "").strip()
    if not s:
        return float("nan")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    return float(s)


def mes_para_numero(mes: object) -> int:
    chave = re.sub(r"[^a-z]", "", norm_nome(str(mes)))[:3]
    return _MES_PARA_NUM.get(chave, 1)


def extrair_hora(valor: object) -> float:
    if pd.isna(valor):
        return float("nan")
    s = str(valor)
    m = re.search(r"(\d{1,2})", s)
    if m:
        return float(m.group(1))
    return float("nan")


def carregar_csv(caminho: Path, nrows: int | None = None) -> pd.DataFrame:
    amostra_bytes = caminho.read_bytes()[:8192]
    melhor: pd.DataFrame | None = None
    kwargs: dict = {}
    if nrows:
        kwargs["nrows"] = nrows
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            texto = amostra_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
        linha = texto.splitlines()[0] if texto.splitlines() else ""
        sep = ";" if linha.count(";") >= linha.count(",") else ","
        try:
            df = pd.read_csv(caminho, encoding=enc, sep=sep, **kwargs)
        except Exception:
            continue
        if len(df.columns) == 1 and "," in str(df.columns[0]):
            df = pd.read_csv(caminho, encoding=enc, sep=",", **kwargs)
        if melhor is None or len(df.columns) > len(melhor.columns):
            melhor = df
    if melhor is None:
        return pd.read_csv(caminho, **kwargs)
    return melhor


def eh_consolidado_mensal(nome: str) -> bool:
    n = nome.lower()
    return "consolidadobe" in n and "publico" not in n


def eh_transacao_diaria(nome: str) -> bool:
    return "transacao_be_publico" in nome.lower()


def preparar_consolidado_mensal(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    c_modal = achar_coluna(cols, ("modal_operadora", "modal"))
    c_qtd = achar_coluna(cols, ("qtd_transacoes", "qtd", "quantidade"))
    c_ano = achar_coluna(cols, ("ano",))
    c_mes = achar_coluna(cols, ("mes",))
    c_vl_trans = achar_coluna(cols, ("vl_transacao", "valor_transacao"))
    c_vl_linha = achar_coluna(cols, ("vl_linha",))
    c_vl_sub = achar_coluna(cols, ("vl_subsidio", "subsidio"))

    if not all([c_modal, c_qtd, c_ano, c_mes]):
        raise ValueError(f"CSV consolidado não reconhecido. Colunas: {cols}")

    out = pd.DataFrame()
    out[COL_MODAL] = df[c_modal].astype(str).str.strip()
    out[COL_QTD] = df[c_qtd].map(parse_numero_br)
    mes_num = df[c_mes].map(mes_para_numero)
    out[COL_MES_REF] = mes_num
    out[COL_DATA] = pd.to_datetime(
        df[c_ano].astype(str) + "-" + mes_num.astype(str) + "-01",
        errors="coerce",
    )
    if c_vl_trans:
        out[COL_VALOR] = df[c_vl_trans].map(parse_numero_br)
    if c_vl_linha:
        out[COL_VALOR_LINHA] = df[c_vl_linha].map(parse_numero_br)
    if c_vl_sub:
        out[COL_SUBSIDIO] = df[c_vl_sub].map(parse_numero_br)
    out[COL_HORA] = mes_num
    return out


def preparar_transacao_diaria(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    c_data = achar_coluna(
        cols,
        (
            "data_da_transacao",
            "data_do_processamento",
            "data",
            "data_transacao",
            "data_referencia",
            "dt_transacao",
        ),
    )
    c_hora = achar_coluna(
        cols,
        ("hora", "hora_dia", "hora_transacao", "faixa_horaria", "faixa_horaria_origem"),
    )
    c_modal = achar_coluna(
        cols,
        (
            "operadora",
            "sindicato",
            "modal_operadora",
            "modal",
            "descricao_da_aplicacao",
            "linha",
        ),
    )
    c_qtd = achar_coluna(cols, ("qtd", "quantidade", "qtd_transacoes"))
    c_dt = achar_coluna(cols, ("data_hora", "datetime", "timestamp"))

    work = df.copy()
    if c_dt and not c_data:
        dt = pd.to_datetime(work[c_dt], errors="coerce", dayfirst=True)
        work[COL_DATA] = dt.dt.normalize()
        work[COL_HORA] = dt.dt.hour
    else:
        if c_data:
            dt = pd.to_datetime(work[c_data], errors="coerce", dayfirst=True)
            work[COL_DATA] = dt.dt.normalize()
            if c_hora:
                work[COL_HORA] = work[c_hora].map(extrair_hora)
            else:
                work[COL_HORA] = dt.dt.hour
        elif c_hora:
            work[COL_HORA] = work[c_hora].map(extrair_hora)

    if c_modal:
        work[COL_MODAL] = work[c_modal].astype(str).str.strip()
    else:
        work[COL_MODAL] = "nao_informado"

    if c_qtd:
        work[COL_QTD] = work[c_qtd].map(parse_numero_br).fillna(1)
    else:
        work[COL_QTD] = 1

    agg_cols = [c for c in (COL_DATA, COL_HORA, COL_MODAL) if c in work.columns]
    if not agg_cols:
        raise ValueError(f"CSV diário sem data/hora. Colunas: {cols}")

    return (
        work.groupby(agg_cols, observed=True)[COL_QTD]
        .sum()
        .reset_index()
    )


def limpar_analise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[COL_DATA] = pd.to_datetime(out[COL_DATA], errors="coerce")
    if COL_HORA in out.columns:
        out[COL_HORA] = pd.to_numeric(out[COL_HORA], errors="coerce")
    out[COL_QTD] = pd.to_numeric(out[COL_QTD], errors="coerce")
    out[COL_MODAL] = out[COL_MODAL].astype(str).str.strip().str.lower()
    obrig = [COL_DATA, COL_QTD, COL_MODAL]
    if COL_HORA in out.columns and out[COL_HORA].notna().any():
        obrig.append(COL_HORA)
    out = out.dropna(subset=obrig)
    out = out.drop_duplicates()
    return out[out[COL_QTD] >= 0]
