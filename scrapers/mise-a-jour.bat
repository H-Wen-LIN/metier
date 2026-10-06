@echo off
rem Met a jour les CSV d'offres. A lancer a la main (double-clic) ou via le Planificateur de taches.
rem Modifiez les recherches ci-dessous : une ligne par commande, toujours avec --mise-a-jour.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
set PY=%~dp0.venv\Scripts\python.exe
set JOURNAL=%~dp0journal-mise-a-jour.log
echo ===== %date% %time% >> "%JOURNAL%"

cd /d "%~dp0jobijoba-scraper"
"%PY%" scraper.py "developpeur web" --ville Clermont-ferrand --ville Paris --pages 3 --sans-sponsorises --mise-a-jour >> "%JOURNAL%" 2>&1

cd /d "%~dp0wttj-scraper"
"%PY%" scraper.py emploi-developpeur-web-paris-75000 --suivre 3 --mise-a-jour >> "%JOURNAL%" 2>&1

echo Mise a jour terminee. Details dans journal-mise-a-jour.log
