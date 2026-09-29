@echo off
rem Render anh NHAP (nhanh) -> renders\draft
cd /d "%~dp0"
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P scripts\render.py -- --mode draft --save-blend
echo.
echo Xong. Xem anh trong thu muc renders\draft
pause
