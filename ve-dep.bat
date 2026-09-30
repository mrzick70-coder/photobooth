@echo off
rem Render anh DEP (Cycles, mat vai phut) -> renders\final
cd /d "%~dp0"
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P scripts\render.py -- --mode final --save-blend
echo.
echo Xong. Xem anh trong thu muc renders\final
pause
