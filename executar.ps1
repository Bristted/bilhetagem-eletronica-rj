# Executa o projeto completo (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Verificando dependencias ===" -ForegroundColor Cyan
python verificar_instalacao.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando bibliotecas..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
    python verificar_instalacao.py
}

Write-Host "`n=== Baixando dados (portal RJ) ===" -ForegroundColor Cyan
python baixar_dados_reais.py

Write-Host "`n=== Rodando analise ===" -ForegroundColor Cyan
python analise_bilhetagem_rj.py

Write-Host "`nConcluido. Veja a pasta saida/" -ForegroundColor Green
