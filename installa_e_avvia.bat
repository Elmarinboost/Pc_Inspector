@echo off
title PC Inspector - Installazione e Avvio
color 0B
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     PC Inspector ^& Comparator            ║
echo  ║     Installazione dipendenze...           ║
echo  ╚══════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRORE] Python non trovato!
    echo  Scarica Python da: https://www.python.org/downloads/
    echo  Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

echo  [1/2] Installazione psutil...
pip install psutil --quiet
if errorlevel 1 (
    echo  [ATTENZIONE] psutil non installato correttamente.
    echo  Prova manualmente: pip install psutil
)

echo  [2/2] Avvio dell'app...
echo.
python C:\Percorso......\pc_inspector.py

if errorlevel 1 (
    echo.
    echo  [ERRORE] L'app e' terminata con un errore.
    pause
)
