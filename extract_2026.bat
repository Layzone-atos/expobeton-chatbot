@echo off
echo ============================================================
echo 🚀 Extraction PDF ExpoBeton 2026
echo ============================================================
echo.

docker run --rm -v "%CD%:/app" -w /app python:3.10-slim bash -c "pip install -q PyPDF2 && python extract_2026.py"

if %errorlevel% == 0 (
    echo.
    echo ✅ Extraction 2026 terminée!
    echo.
    echo 📁 Fichier créé: docs\Brochure_ExpoBeton_RDC_2026.txt
    echo.
) else (
    echo.
    echo ❌ Erreur lors de l'extraction
    echo.
)

pause
