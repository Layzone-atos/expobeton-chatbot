@echo off
echo ============================================================
echo 🚀 Extraction AUTOMATIQUE de TOUS les PDFs avec Docker
echo ============================================================
echo.
echo 📦 Installation de PyPDF2 et extraction...
echo ⏰ Cela peut prendre 5-10 minutes pour 187 PDFs
echo.

docker run --rm -v "%CD%:/app" -w /app python:3.10-slim bash -c "pip install -q PyPDF2 && python extract_all.py"

if %errorlevel% == 0 (
    echo.
    echo ============================================================
    echo ✅ EXTRACTION COMPLÈTE TERMINÉE!
    echo ============================================================
    echo.
    echo 📁 Tous les fichiers .txt sont dans: docs\
    echo.
    echo 📋 Prochaine étape:
    echo    git add docs/*.txt
    echo    git commit -m "Add all extracted PDFs from all editions"
    echo    git push
    echo.
) else (
    echo.
    echo ❌ Une erreur s'est produite
    echo.
)

pause
