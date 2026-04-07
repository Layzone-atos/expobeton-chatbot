@echo off
echo ============================================================
echo 🚀 Extraction PDF → TXT avec Docker (pas besoin de Python!)
echo ============================================================
echo.

REM Vérification que pdf_source_* existe
for /d %%D in (pdf_source_*) do (
    goto found
)

echo ❌ Aucun dossier pdf_source_* trouvé!
echo.
echo 📁 Créez des dossiers comme:
echo    pdf_source_2025\     ^<-- Mettez vos PDFs 2025 ici
echo    pdf_source_2024\     ^<-- Mettez vos PDFs 2024 ici
echo.
pause
exit /b 1

:found
echo ✅ Dossier(s) PDF trouvé(s)!
echo.
echo 📦 Installation de PyPDF2 dans Docker...
echo.

REM Extraction avec Docker (automatique sur choix 5 pour TOUT)
docker run --rm -v "%CD%:/app" -w /app python:3.10-slim bash -c "pip install -q PyPDF2 && echo '5' | python extract_pdfs.py"

if %errorlevel% == 0 (
    echo.
    echo ============================================================
    echo ✅ EXTRACTION TERMINÉE!
    echo ============================================================
    echo.
    echo 📁 Les fichiers .txt sont dans le dossier: docs\
    echo.
    echo 📋 Prochaine étape:
    echo    1. Vérifiez les fichiers .txt dans docs\
    echo    2. Redéployez sur Railway pour que le bot les utilise
    echo.
) else (
    echo.
    echo ❌ Une erreur s'est produite
    echo.
    echo 💡 Assurez-vous que Docker est installé et démarré
    echo.
)

pause
