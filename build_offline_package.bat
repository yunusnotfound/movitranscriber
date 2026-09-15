@echo off
setlocal
cd /d "%~dp0"

rem Sirket proxy'si varsa asagidaki satirlari acip duzenleyin (pip, python.org ve Hugging Face icin):
rem set HTTPS_PROXY=http://proxy.sirket.local:8080
rem set HTTP_PROXY=http://proxy.sirket.local:8080

echo [MoviTranscriber] Tasinabilir paket hazirlaniyor (python\ + packages\ + models\)...
echo Ek secenekler icin: build_offline_package.bat --all-models  veya  --model small
python -u tools\build_offline_package.py %*
if errorlevel 1 (
    echo.
    echo Paketleme tamamlanamadi. Ag/proxy sorunuysa ayni komutu tekrar calistirin; kaldigi yerden devam eder.
)
pause
