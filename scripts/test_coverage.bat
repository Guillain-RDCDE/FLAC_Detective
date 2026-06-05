@echo off
echo ========================================
echo Testing Coverage Configuration Locally
echo ========================================
echo.

echo [1/4] Cleaning previous coverage data...
if exist .coverage del .coverage
if exist coverage.xml del coverage.xml
if exist htmlcov rmdir /s /q htmlcov
echo Done.
echo.

echo [2/4] Running tests with coverage...
pytest tests/ --cov=flac_detective --cov-report=xml --cov-report=term-missing --cov-report=html --cov-fail-under=80
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Tests failed or coverage below 80%%
    pause
    exit /b 1
)
echo Done.
echo.

echo [3/4] Checking coverage.xml file...
if exist coverage.xml (
    echo SUCCESS: coverage.xml generated successfully
    dir coverage.xml
) else (
    echo ERROR: coverage.xml not found
    pause
    exit /b 1
)
echo.

echo [4/4] Coverage HTML report location...
if exist htmlcov\index.html (
    echo SUCCESS: HTML report generated at htmlcov\index.html
    echo You can open it in your browser to view the coverage report
    echo.
    set /p OPEN="Open coverage report in browser? (Y/N): "
    if /i "%OPEN%"=="Y" start htmlcov\index.html
) else (
    echo WARNING: HTML report not found
)
echo.

echo ========================================
echo Coverage test completed successfully!
echo ========================================
echo.
echo The coverage.xml file is ready to be uploaded to Codecov.
echo The CI workflow will automatically upload it when running on GitHub Actions.
echo.
pause
