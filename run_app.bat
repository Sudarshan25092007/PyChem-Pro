@echo off
echo Starting SMILES to 3D Molecular Viewer...
echo.

REM Use portable Python
set PYTHON_PATH=D:\Portable_Python_3.10.5_x64\App\Python\python.exe

echo Using Python:
"%PYTHON_PATH%" --version
echo.

REM Run the main application
"%PYTHON_PATH%" main.py

pause
