@echo off
echo ============================================================
echo Installation de PyPDF2 pour l'extraction PDF
echo ============================================================
echo.

REM Essai avec py
py -m pip install PyPDF2
if %errorlevel% == 0 goto success

REM Essai avec python3
python3 -m pip install PyPDF2
if %errorlevel% == 0 goto success

REM Essai avec python
python -m pip install PyPDF2
if %errorlevel% == 0 goto success

echo.
echo ❌ Python n'a pas été trouvé!
echo.
echo 💡 Solutions:
echo    1. Installez Python 3.10 depuis https://python.org
echo    2. OU utilisez Docker (déjà configuré dans le projet)
echo.
pause
exit /b 1

:success
echo.
echo ✅ PyPDF2 installé avec succès!
echo.
echo 📋 Prochaine étape:
echo    1. Créez le dossier: pdf_source_2025
echo    2. Mettez vos PDFs dedans
echo    3. Lancez: run_extract.bat
echo.
pause
