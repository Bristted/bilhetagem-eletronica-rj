# Análise da bilhetagem eletrônica — RJ (SETRAM/SBE)

Projeto extensionista: demanda de transporte público com dados abertos do Estado do Rio de Janeiro.

| Item | Detalhe |
|------|---------|
| **Disciplina** | Tópicos de Big Data em Python (2026.1) |
| **Autores** | Lucas Martins Matos e Gabriel Belo da Silva |
| **Dados** | [Portal SETRAM SBE — dados abertos RJ](https://www.dadosabertos.rj.gov.br/dataset/setram_sbe) |

---

## Como rodar (quem clonou do GitHub)

### 1. Pré-requisitos

- [Python 3.11+](https://www.python.org/downloads/) (marcar **Add to PATH** na instalação)
- [Git](https://git-scm.com/download/win) (opcional, só para clonar)

### 2. Clonar o repositório

```powershell
git clone https://github.com/Bristted/bilhetagem-eletronica-rj.git
cd bilhetagem-eletronica-rj
```

### 3. Instalar bibliotecas (Pandas, etc.)

```powershell
python -m pip install -r requirements.txt
python verificar_instalacao.py
```

Deve aparecer `Ambiente pronto para rodar o projeto.`

### 4. Baixar dados oficiais

```powershell
python baixar_dados_reais.py
```

- Consolidados mensais (jan–mai/2025) → `dados/consolidado/`
- Amostra diária 01–07/mai/2025 → `dados/publico/` (arquivos grandes)

> Se o repositório já incluir CSVs em `dados/consolidado/`, a análise mensal roda mesmo sem baixar tudo.

### 4. Criar pasta chamada SAIDA

### 6. Executar a análise

```powershell
python analise_bilhetagem_rj.py
```

Resultados: pasta **`saida/`** (gráficos `.png` e tabelas `.csv`).

---

## Atalho no Windows

Duplo clique em **`executar.bat`** (instala dependências, baixa dados e roda a análise).

Ou no PowerShell:

```powershell
.\executar.ps1
```

---

## Estrutura do repositório

```
projeto_bilhetagem_rj/
├── analise_bilhetagem_rj.py   # Pipeline principal
├── baixar_dados_reais.py      # Download no portal RJ
├── setram_utils.py            # Leitura/limpeza dos CSVs
├── verificar_instalacao.py    # Testa Pandas e demais libs
├── requirements.txt           # Dependências pip
├── executar.bat / executar.ps1
├── dados/
│   ├── consolidado/           # CSV mensal por modal
│   └── publico/               # CSV diário (amostra)
└── saida/                     # Saídas geradas
```

---

## Ferramentas Python utilizadas

- **Pandas** — leitura e agregação dos CSVs  
- **NumPy** — operações numéricas  
- **Matplotlib / Seaborn** — gráficos  
- **Scikit-learn** — regressão linear simples  

---

## Problemas comuns

| Erro | Solução |
|------|---------|
| `python não é reconhecido` | Reinstale Python marcando **Add to PATH** |
| `No module named pandas` | `python -m pip install -r requirements.txt` |
| `pip não é reconhecido` | Use `python -m pip install -r requirements.txt` |
| Download muito lento | Use só `dados/consolidado/` para teste; diários são opcionais |

---

## Licença dos dados

Dados públicos do Governo do Estado do Rio de Janeiro (SETRAM), conforme portal de dados abertos.
