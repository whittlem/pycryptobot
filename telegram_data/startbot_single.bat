@ECHO OFF
set market=%1
shift
set params=%1

:loop
shift
echo %1
if [%1]==[] goto afterloop
set params=%params% %1
goto loop
:afterloop

echo %market%
echo %params%
cd d:\LiveBot
CALL start powershell -NoExit -Command "$host.UI.RawUI.WindowTitle = '%market%' ; python3 pycryptobot.py --market %market% --logfile './logs/coinbase_%%i.log'  %params%"
