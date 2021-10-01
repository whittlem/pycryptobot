@echo off

ECHO Starting Coinbase Pro Bots...
cd d:\Livebot
REM git pull

SETLOCAL
SET "var1="
SET "var2="
FOR /f "tokens=*" %%a IN (d:\coinbasepropairs.txt) DO (
	CALL SET "var1=%%var2%%"
	CALL SET "var2=%%a"
    IF DEFINED var1 (
	   CALL ECHO %%var1%%
	   CALL ECHO %%var2%%
	   CALL start powershell -NoExit -Command "$host.UI.RawUI.WindowTitle = '%%var1%%' ; python3 pycryptobot.py --exchange coinbasepro --market %%var1%% --logfile './logs/coinbase_%%var1%%.log'  %%var2%%"
	   SET "var1="
	   SET "var2="
	   TIMEOUT /T 15
	
	)

)

@echo off

ECHO Starting Binance Bots...
cd d:\livebot

SETLOCAL
SET "var1="
SET "var2="
FOR /f "tokens=*" %%a IN (d:\binancepairs.txt) DO (
 CALL SET "var1=%%var2%%"
 CALL SET "var2=%%a"
 IF DEFINED var1 (
	CALL ECHO %%var1%%
	CALL ECHO %%var2%%
	CALL start powershell -NoExit -Command "$host.UI.RawUI.WindowTitle = '%%var1%%' ; python3 pycryptobot.py --exchange binance --market %%var1%% --logfile './logs/binance_%%var1%%.log'  %%var2%%"
	SET "var1="
	SET "var2="
    TIMEOUT /T 18
  )

)

pause