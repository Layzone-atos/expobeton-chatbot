@echo off
echo ============================================================
echo 🚀 Extraction PDF → TXT pour ExpoBeton RDC
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
echo    pdf_source_2023\     ^<-- Mettez vos PDFs 2023 ici
echo    ...
echo.
pause
exit /b 1

:found

REM Essai avec py
py extract_pdfs.py
if %errorlevel% == 0 goto end

REM Essai avec python3
python3 extract_pdfs.py
if %errorlevel% == 0 goto end

REM Essai avec python
python extract_pdfs.py

:end
echo.
pause
