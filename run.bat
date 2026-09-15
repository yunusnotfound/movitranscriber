@echo off
setlocal
cd /d "%~dp0"

rem Sirket proxy'si varsa ve model indirilmesi gerekiyorsa asagidaki satiri acip duzenleyin
rem (tasinabilir pakette modeller klasorde geldigi icin genelde gerekmez):
rem set HTTPS_PROXY=http://proxy.sirket.local:8080

rem ---- 1) Tasinabilir kurulum: python\ ve packages\ varsa hicbir sey kurulmaz, internet gerekmez.
if exist "python\python.exe" if exist "packages\gradio" (
    set "PY=python\python.exe"
    echo [MoviTranscriber] Tasinabilir kurulum bulundu.
    goto :run
)

rem ---- 2) Gelistirici kurulumu: sistemdeki Python ile sanal ortam (internet gerekir).
if not exist ".venv\Scripts\python.exe" (
    echo [MoviTranscriber] Sanal ortam olusturuluyor...
    python -m venv .venv
    if errorlevel 1 (
        echo Python bulunamadi. Ya https://www.python.org/downloads/ adresinden Python 3.11+ kurun,
        echo ya da tasinabilir paketi kullanin: python tools\build_offline_package.py
        pause
        exit /b 1
    )
)
set "PY=.venv\Scripts\python.exe"

"%PY%" -c "import faster_whisper, gradio" >nul 2>&1
if errorlevel 1 (
    echo [MoviTranscriber] Bagimliliklar kuruluyor, ilk kurulum birkac dakika surebilir...
    "%PY%" -m pip install --upgrade pip >nul
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Kurulum basarisiz oldu. Internet baglantinizi veya proxy ayarini kontrol edin.
        pause
        exit /b 1
    )
)

:run
echo [MoviTranscriber] Baslatiliyor... Kapatmak icin bu pencereyi kapatin.
"%PY%" app.py
pause
