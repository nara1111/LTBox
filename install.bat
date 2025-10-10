@echo off
setlocal

echo --- Required Files Installer ---
echo.

:: ======================================================
:: Variable Definitions
:: ======================================================
set "TOOLS_DIR=%~dp0tools"
set "KEY_DIR=%~dp0key"
set "PYTHON_DIR=%~dp0python3"
set "PYTHON_VERSION=3.14.0"
set "PYTHON_ZIP_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_ZIP_PATH=%~dp0python_embed.zip"
set "PYTHON_PTH_FILE_SRC=%TOOLS_DIR%\\python314._pth"
set "PYTHON_PTH_FILE_DST=%PYTHON_DIR%\\python314._pth"
set "GETPIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "GETPIP_PATH=%PYTHON_DIR%\\get-pip.py"
set "FETCH_VERSION=v0.4.6"
set "FETCH_URL=https://github.com/gruntwork-io/fetch/releases/download/%FETCH_VERSION%/fetch_windows_amd64.exe"
set "FETCH_EXE=%TOOLS_DIR%\\fetch.exe"


:: ======================================================
:: Create Directories
:: ======================================================
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"
if not exist "%KEY_DIR%" mkdir "%KEY_DIR%"


:: ======================================================
:: Download Python and Set Up Environment
:: ======================================================
echo [*] Checking for Python...
if exist "%PYTHON_DIR%\\python.exe" goto python_exists
echo [!] Python not found.
echo Attempting to download Python %PYTHON_VERSION%...
curl -L "%PYTHON_ZIP_URL%" -o "%PYTHON_ZIP_PATH%"
if not exist "%PYTHON_ZIP_PATH%" (
    echo [!] Download failed.
    goto :eof
)
echo [+] Download successful.
echo [*] Extracting Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP_PATH%' -DestinationPath '%PYTHON_DIR%' -Force"
del "%PYTHON_ZIP_PATH%"
if exist "%PYTHON_PTH_FILE_SRC%" (
    echo [*] Copying PTH file...
    copy "%PYTHON_PTH_FILE_SRC%" "%PYTHON_PTH_FILE_DST%"
)
echo [*] Checking for pip...
if exist "%PYTHON_DIR%\\Scripts\\pip.exe" goto pip_exists
echo [!] pip not found.
echo Attempting to download get-pip.py...
curl -L "%GETPIP_URL%" -o "%GETPIP_PATH%"
if not exist "%GETPIP_PATH%" (
    echo [!] Download failed.
    goto :eof
)
echo [+] Download successful.
echo [*] Installing pip...
"%PYTHON_DIR%\\python.exe" "%GETPIP_PATH%"
del "%GETPIP_PATH%"
:pip_exists
:python_exists
echo.
echo [*] Checking for requests module...
"%PYTHON_DIR%\\python.exe" -c "import requests" 2>nul
if %errorlevel% equ 0 goto requests_exists
echo [!] 'requests' module not found.
echo Attempting to install...
"%PYTHON_DIR%\\Scripts\\pip.exe" install requests
:requests_exists
echo.
echo [*] Checking for cryptography module...
"%PYTHON_DIR%\\python.exe" -c "import cryptography" 2>nul
if %errorlevel% equ 0 goto cryptography_exists
echo [!] 'cryptography' module not found.
echo Attempting to install...
"%PYTHON_DIR%\\Scripts\\pip.exe" install cryptography
:cryptography_exists
echo.


:: ======================================================
:: Download Other Tools
:: ======================================================
echo [*] Checking for fetch.exe...
if exist "%FETCH_EXE%" goto fetch_exists
echo [!] 'fetch.exe' not found.
echo Attempting to download...
curl -L "%FETCH_URL%" -o "%FETCH_EXE%"
if exist "%FETCH_EXE%" (echo [+] Download successful.) else (echo [!] Download failed.)
:fetch_exists
echo.

:: ======================================================
:: Download avbtool and Keys
:: ======================================================
set "AVB_DIR=%TOOLS_DIR%\avb"
set "AVB_TOOL_PATH=%AVB_DIR%\avbtool.py"
set "AVB_ARCHIVE_URL=https://android.googlesource.com/platform/external/avb/+archive/refs/heads/main.tar.gz"
set "TEMP_ARCHIVE=%TOOLS_DIR%\avb_main.tar.gz"

echo [*] Checking for avbtool and test keys...
if exist "%AVB_TOOL_PATH%" (
    echo [+] avbtool and keys are already present.
) else (
    echo [*] avbtool not found. Downloading from AOSP...
    if not exist "%AVB_DIR%" mkdir "%AVB_DIR%"

    echo [*] Downloading avb source archive...
    curl -L "%AVB_ARCHIVE_URL%" -o "%TEMP_ARCHIVE%"
    if errorlevel 1 (
        echo [!] Failed to download the archive.
        goto :error
    )

    echo [*] Extracting required files...
    tar -xzf "%TEMP_ARCHIVE%" -C "%AVB_DIR%" avbtool.py
    if errorlevel 1 (
        echo [!] Failed to extract avbtool.py.
        goto :error
    )
    tar -xzf "%TEMP_ARCHIVE%" -C "%AVB_DIR%" --strip-components=2 test/data/testkey_rsa2048.pem
    if errorlevel 1 (
        echo [!] Failed to extract testkey_rsa2048.pem.
        goto :error
    )
    tar -xzf "%TEMP_ARCHIVE%" -C "%AVB_DIR%" --strip-components=2 test/data/testkey_rsa4096.pem
    if errorlevel 1 (
        echo [!] Failed to extract testkey_rsa4096.pem.
        goto :error
    )

    echo [+] Extraction successful.
    del "%TEMP_ARCHIVE%"
)
echo.

:error
if exist "%TEMP_ARCHIVE%" del "%TEMP_ARCHIVE%"

echo --- Installation complete ---
pause
endlocal