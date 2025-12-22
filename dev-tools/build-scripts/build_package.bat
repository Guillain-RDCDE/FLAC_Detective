@echo off
echo Cleaning build directories...
timeout /t 2 /nobreak >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q src\flac_detective.egg-info 2>nul

echo Building package...
python -m build

echo.
echo Checking dist directory...
dir dist\

echo.
echo Validating package...
twine check dist\flac_detective-0.9.6*
