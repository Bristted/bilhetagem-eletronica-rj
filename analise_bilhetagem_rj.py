from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from setram_utils import (
    COL_DATA,
    COL_HORA,
    COL_MES_REF,
    COL_MODAL,
    COL_QTD,
    COL_SUBSIDIO,
    COL_VALOR,
    COL_VALOR_LINHA,
    carregar_csv,
    eh_consolidado_mensal,
    eh_transacao_diaria,
    limpar_analise,
    preparar_consolidado_mensal,
    preparar_transacao_diaria,
)

BASE_DIR = Path(__file__).resolve().parent
DADOS_DIR = BASE_DIR / "dados"
PASTA_SAIDA = BASE_DIR / "saida"
RNG_SEED = 42
MAX_LINHAS_DIARIO = 300_000


def _listar_csvs(pasta: Path, filtro) -> list[Path]:
    if not pasta.is_dir():
        return []
    arquivos = [p for p in pasta.rglob("*.csv") if filtro(p.name)]
    return sorted(set(arquivos), key=lambda p: p.name.lower())


def carregar_todos_consolidados() -> pd.DataFrame:
    pastas = [DADOS_DIR / "consolidado", DADOS_DIR]
    frames: list[pd.DataFrame] = []
    vistos: set[str] = set()
    for pasta in pastas:
        for path in _listar_csvs(pasta, eh_consolidado_mensal):
            chave = path.name.lower()
            if chave in vistos:
                continue
            vistos.add(chave)
            print(f"[consolidado] lendo {path.name}")
            raw = carregar_csv(path)
            frames.append(preparar_consolidado_mensal(raw))
    if not frames:
        return pd.DataFrame()
    return limpar_analise(pd.concat(frames, ignore_index=True))


def carregar_amostra_diaria() -> pd.DataFrame:
    pasta = DADOS_DIR / "publico"
    frames: list[pd.DataFrame] = []
    for path in _listar_csvs(pasta, eh_transacao_diaria):
        print(f"[diário] lendo até {MAX_LINHAS_DIARIO:,} linhas de {path.name}")
        raw = carregar_csv(path, nrows=MAX_LINHAS_DIARIO)
        try:
            prep = preparar_transacao_diaria(raw)
            frames.append(prep)
        except ValueError as exc:
            print(f"  [aviso] {path.name}: {exc}")
    if not frames:
        return pd.DataFrame()
    return limpar_analise(pd.concat(frames, ignore_index=True))


def regressao_simples(
    df: pd.DataFrame, col_x: str, rotulo: str
) -> tuple[LinearRegression, dict, str]:
    if len(df) < 2:
        raise ValueError(f"Poucos dados para regressão ({rotulo}).")
    xy = df[[col_x, COL_QTD]].dropna()
    X = xy[[col_x]].values
    y = xy[COL_QTD].values
    test_size = 0.25 if len(xy) >= 8 else max(1, len(xy) // 4)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RNG_SEED
    )
    modelo = LinearRegression()
    modelo.fit(X_train, y_train)
    pred = modelo.predict(X_test)
    metricas = {
        "variavel_x": rotulo,
        "coef_angular": float(modelo.coef_[0]),
        "intercepto": float(modelo.intercept_),
        "r2_teste": float(r2_score(y_test, pred)) if len(y_test) > 1 else float("nan"),
        "mae_teste": float(mean_absolute_error(y_test, pred)),
        "n_observacoes": int(len(xy)),
    }
    print(f"\n--- Regressão ({rotulo}) ---")
    for k, v in metricas.items():
        print(f"  {k}: {v}")
    return modelo, metricas, col_x


def analise_consolidado(df: pd.DataFrame) -> None:
    if df.empty:
        print("[consolidado] sem dados — rode baixar_dados_reais.py")
        return

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    print("\n--- Estatísticas descritivas (transações) ---")
    print(df[COL_QTD].describe())

    freq_modal = df.groupby(COL_MODAL)[COL_QTD].sum().sort_values(ascending=False)
    print("\n--- Frequência por modal (total no período) ---")
    print(freq_modal)
    freq_modal.to_csv(PASTA_SAIDA / "frequencia_modal_total.csv", encoding="utf-8")

    serie = df.groupby([COL_DATA, COL_MODAL])[COL_QTD].sum().reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    for modal, grp in serie.groupby(COL_MODAL):
        ax.plot(grp[COL_DATA], grp[COL_QTD], marker="o", label=modal)
    ax.set_title("Evolução mensal da demanda por modal (consolidado SETRAM)")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Quantidade de transações")
    ax.legend(loc="best", fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "serie_temporal_modal.png", dpi=150)
    plt.close(fig)

    if COL_SUBSIDIO in df.columns and COL_VALOR_LINHA in df.columns:
        ultimo = df.sort_values(COL_DATA).groupby(COL_MODAL).last().reset_index()
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        ultimo.plot(x=COL_MODAL, y=COL_QTD, kind="bar", ax=axes[0], color="steelblue", legend=False)
        axes[0].set_title("Transações por modal (último mês)")
        axes[0].tick_params(axis="x", rotation=25)

        x = np.arange(len(ultimo))
        w = 0.25
        axes[1].bar(x - w, ultimo[COL_VALOR], width=w, label="Vl transação")
        axes[1].bar(x, ultimo[COL_VALOR_LINHA], width=w, label="Vl linha")
        axes[1].bar(x + w, ultimo[COL_SUBSIDIO], width=w, label="Vl subsídio")
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(ultimo[COL_MODAL], rotation=25, ha="right")
        axes[1].set_title("Valores financeiros por modal (último mês)")
        axes[1].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(PASTA_SAIDA / "subsidios_e_valores_modal.png", dpi=150)
        plt.close(fig)

        ultimo[[COL_MODAL, COL_QTD, COL_VALOR, COL_VALOR_LINHA, COL_SUBSIDIO]].to_csv(
            PASTA_SAIDA / "resumo_financeiro_modal.csv", index=False, encoding="utf-8"
        )

    if COL_VALOR in df.columns:
        modelo, metricas, col_x = regressao_simples(df, COL_VALOR, "valor_transacao")
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(df[col_x], df[COL_QTD], s=60, alpha=0.8)
        xs = np.linspace(df[col_x].min(), df[col_x].max(), 50).reshape(-1, 1)
        ax.plot(xs, modelo.predict(xs), color="darkred", lw=2)
        ax.set_xlabel("Valor das transações (R$)")
        ax.set_ylabel("Qtd. transações")
        ax.set_title("Regressão: volume × valor (consolidado)")
        fig.tight_layout()
        fig.savefig(PASTA_SAIDA / "regressao_consolidado_valor.png", dpi=150)
        plt.close(fig)
        pd.Series(metricas).to_csv(
            PASTA_SAIDA / "metricas_regressao_consolidado.csv", encoding="utf-8"
        )

    fig, ax = plt.subplots(figsize=(8, 4))
    freq_modal.plot(kind="bar", ax=ax, color="steelblue")
    ax.set_title("Distribuição de frequência — transações por modal")
    ax.set_ylabel("Transações")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "freq_por_modal.png", dpi=150)
    plt.close(fig)


def analise_diaria(df: pd.DataFrame) -> None:
    if df.empty:
        print("[diário] sem dados — baixe a pasta publico/ com baixar_dados_reais.py")
        return

    print(f"\n[diário] registros agregados: {len(df)}")
    print("\n--- Estatísticas descritivas (amostra diária) ---")
    print(df[COL_QTD].describe())

    freq_hora = df.groupby(COL_HORA)[COL_QTD].sum().sort_index()
    print("\n--- Frequência por hora do dia ---")
    print(freq_hora)
    freq_hora.to_csv(PASTA_SAIDA / "frequencia_por_hora.csv", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 4))
    freq_hora.plot(kind="bar", ax=ax, color="teal")
    ax.set_title("Demanda por hora (amostra: 01–07/mai/2025)")
    ax.set_xlabel("Hora do dia")
    ax.set_ylabel("Transações")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "freq_por_hora.png", dpi=150)
    plt.close(fig)

    pico = (
        df.groupby([COL_HORA, COL_MODAL])[COL_QTD]
        .sum()
        .reset_index()
        .sort_values(COL_QTD, ascending=False)
    )
    pico.head(15).to_csv(PASTA_SAIDA / "top_horarios_modal.csv", index=False, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10, 5))
    top_modais = df.groupby(COL_MODAL)[COL_QTD].sum().nlargest(4).index
    for modal in top_modais:
        sub = df[df[COL_MODAL] == modal].groupby(COL_HORA)[COL_QTD].sum()
        ax.plot(sub.index, sub.values, marker="o", label=modal)
    ax.set_title("Perfil horário por modal (top 4)")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Transações")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "perfil_horario_por_modal.png", dpi=150)
    plt.close(fig)

    modelo, metricas, col_x = regressao_simples(df, COL_HORA, "hora_dia")
    fig, ax = plt.subplots(figsize=(8, 5))
    agg = df.groupby(COL_HORA)[COL_QTD].sum().reset_index()
    ax.scatter(agg[col_x], agg[COL_QTD], s=80)
    xs = np.linspace(agg[col_x].min(), agg[col_x].max(), 50).reshape(-1, 1)
    ax.plot(xs, modelo.predict(xs), color="darkred", lw=2)
    ax.set_xlabel("Hora do dia")
    ax.set_ylabel("Transações (agregadas)")
    ax.set_title("Regressão linear: demanda ~ hora")
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / "regressao_simples.png", dpi=150)
    plt.close(fig)
    pd.Series(metricas).to_csv(PASTA_SAIDA / "metricas_regressao_horario.csv", encoding="utf-8")


def mover_csv_antigo() -> None:
    """Move CSV solto na raiz de dados/ para consolidado/."""
    for path in DADOS_DIR.glob("*.csv"):
        if eh_consolidado_mensal(path.name) and "amostra" not in path.name.lower():
            dest = DADOS_DIR / "consolidado" / path.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                path.rename(dest)
                print(f"[organização] movido para {dest}")


def main() -> int:
    print("=" * 60)
    print("Análise SETRAM — Bilhetagem Eletrônica RJ")
    print("=" * 60)
    mover_csv_antigo()

    df_cons = carregar_todos_consolidados()
    print(f"\n>>> Bloco 1: Consolidado mensal ({len(df_cons)} registros)")
    analise_consolidado(df_cons)

    df_dia = carregar_amostra_diaria()
    print(f"\n>>> Bloco 2: Amostra diária / horário ({len(df_dia)} registros agregados)")
    analise_diaria(df_dia)

    print(f"\nFiguras e tabelas em: {PASTA_SAIDA.resolve()}")
    print("Pipeline concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
