@echo off
rem Installation en un double-clic : Python, dependances, tache quotidienne, premiere mise a jour.
setlocal
cd /d "%~dp0"
echo ==================================================
echo   Installation de la mise a jour des offres
echo ==================================================
echo.

rem --- 1. Trouver Python 3 ---
set "PYBASE="
py -3 --version >nul 2>&1
if not errorlevel 1 (set "PYBASE=py -3" & goto python_ok)
python --version 2>nul | findstr /b /c:"Python 3" >nul
if not errorlevel 1 (set "PYBASE=python" & goto python_ok)
goto pas_de_python
:python_ok
echo [1/4] Python trouve :
%PYBASE% --version

rem --- 2. Environnement Python et dependances ---
echo.
echo [2/4] Installation des dependances, patientez...
if not exist ".venv\Scripts\python.exe" %PYBASE% -m venv .venv
if not exist ".venv\Scripts\python.exe" goto erreur
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r jobijoba-scraper\requirements.txt
if errorlevel 1 goto erreur

rem --- 3. Tache planifiee : tous les jours a 9 h, rattrapee au demarrage si le PC etait eteint ---
echo.
echo [3/4] Programmation de la mise a jour tous les jours a 9 h...
set "DOSSIER=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d = $env:DOSSIER; $bat = [char]34 + (Join-Path $d 'mise-a-jour.bat') + [char]34; $a = New-ScheduledTaskAction -Execute $bat -Argument 'auto' -WorkingDirectory $d; $t = New-ScheduledTaskTrigger -Daily -At '09:00'; $s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1); Register-ScheduledTask -TaskName 'Mise a jour des offres' -Description 'Scrapers Jobijoba et Welcome to the Jungle' -Action $a -Trigger $t -Settings $s -Force | Out-Null"
if errorlevel 1 goto erreur
echo     Tache "Mise a jour des offres" creee.

rem --- 4. Premiere mise a jour ---
echo.
echo [4/4] Premiere recuperation des offres (quelques minutes)...
call "%~dp0mise-a-jour.bat" auto
echo.
echo --------------------------------------------------
powershell -NoProfile -Command "Get-Content -Encoding UTF8 -Tail 20 -LiteralPath (Join-Path $env:DOSSIER 'journal-mise-a-jour.log')"
echo --------------------------------------------------
echo.
echo C'est installe. Vos offres :
echo   %~dp0jobijoba-scraper\data\offres.csv
echo   %~dp0wttj-scraper\data\offres_wttj.csv
echo Elles se mettront a jour toutes seules chaque jour a 9 h.
echo.
pause
exit /b 0

:pas_de_python
echo Python 3 n'est pas installe sur cet ordinateur.
echo La page de telechargement va s'ouvrir. Installez Python en cochant
echo "Add python.exe to PATH" sur le premier ecran, puis relancez installer.bat.
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1

:erreur
echo.
echo Une erreur est survenue : lisez les messages ci-dessus.
echo Vous pouvez relancer installer.bat sans risque.
pause
exit /b 1
