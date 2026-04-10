@echo off
setlocal enabledelayedexpansion
echo Starting PyChem -- Molecular Viewer and Cheminformatics Software
echo.

REM Define your possible Python paths here, separated by semicolons
set "SEARCH_PATHS=E:\D-Drive\Portable_Python_3.10.5_x64\App\Python\python.exe;E:\Portable_Python_3.10.5_x64\App\Python\python.exe;D:\Portable_Python_3.10.5_x64\App\Python\python.exe;C:\Python310\python.exe"

set "PYTHON_PATH="

REM Loop through the paths to find the first one that exists
for %%A in ("%SEARCH_PATHS:;=" "%") do (
    if exist %%~A (
        set "PYTHON_PATH=%%~A"
        goto :FOUND
    )
)

:NOT_FOUND
echo ERROR: python.exe was not found in any of the specified locations.
pause
exit /b

:FOUND
echo Using Python found at: %PYTHON_PATH%
"%PYTHON_PATH%" --version
echo.

REM Run the main application
"%PYTHON_PATH%" main.py

pause
