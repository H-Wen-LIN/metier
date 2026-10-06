@echo off
rem Supprime la tache quotidienne. Les fichiers CSV deja recuperes sont conserves.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName 'Mise a jour des offres' -Confirm:$false -ErrorAction SilentlyContinue"
echo La mise a jour quotidienne est arretee. Vos fichiers CSV sont conserves.
pause
