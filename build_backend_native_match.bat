@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64
cd /d "C:\Users\abdul\Projects\football_manager\backend"
"C:\Program Files\CMake\bin\cmake.exe" -S . -B build -A x64 -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit /b 1
"C:\Program Files\CMake\bin\cmake.exe" --build build --config Release

