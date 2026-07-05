Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c taskkill /F /IM cloudflared.exe 2>nul & taskkill /F /IM python.exe 2>nul & timeout /t 2 /nobreak >nul", 0, True
WshShell.Run "C:\Users\artem\AppData\Local\Programs\Python\Python314\python.exe C:\Users\artem\AppData\Local\Temp\watchdog2.py", 0, False
