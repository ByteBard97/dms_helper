@echo off

echo Activating virtual environment...
call .\\.venv\\Scripts\\activate.bat

echo Running DMS Helper GUI...
.\\.venv\\Scripts\\python.exe src\\dms_gui.py

echo Script finished. Press any key to close this window...
pause 