echo off
set LOCALHOST=%COMPUTERNAME%
set KILL_CMD="C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent/ntbin/win64/winkill.exe"

start "tell.exe" /B "C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\tell.exe" DESKTOP-4KC1TKA 53856 CLEANUP_EXITING
timeout /t 1
"C:\PROGRA~1\ANSYSI~1\ANSYSS~1\v261\fluent\ntbin\win64\kill.exe" tell.exe
if /i "%LOCALHOST%"=="DESKTOP-4KC1TKA" (%KILL_CMD% 14544) 
if /i "%LOCALHOST%"=="DESKTOP-4KC1TKA" (%KILL_CMD% 4736) 
if /i "%LOCALHOST%"=="DESKTOP-4KC1TKA" (%KILL_CMD% 25936)
del "C:\Users\jaeyk\Documents\two-staged-rocket-preliminary-design-cfd\CFD\Stage1\cleanup-fluent-DESKTOP-4KC1TKA-4736.bat"
