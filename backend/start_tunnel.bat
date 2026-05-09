@echo off
:: start_tunnel.bat — expose the local backend (port 8765) via Cloudflare Tunnel
:: The printed URL is what you set as VITE_API_BASE_URL in GitHub Secrets.
::
:: First run: downloads cloudflared automatically.
:: Subsequent runs: just starts the tunnel.

set CLOUDFLARED=%~dp0cloudflared.exe

if not exist "%CLOUDFLARED%" (
    echo [tunnel] Downloading cloudflared...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CLOUDFLARED%'"
    if errorlevel 1 (
        echo [tunnel] Download failed. Get cloudflared from https://github.com/cloudflare/cloudflared/releases
        pause
        exit /b 1
    )
    echo [tunnel] Downloaded.
)

echo.
echo [tunnel] Starting Cloudflare Tunnel for http://localhost:8765
echo [tunnel] Look for the line:  https://xxxx.trycloudflare.com
echo [tunnel] Copy that URL ^> GitHub repo Settings ^> Secrets ^> VITE_API_BASE_URL
echo [tunnel] Then push to main to redeploy GitHub Pages.
echo.
"%CLOUDFLARED%" tunnel --url http://localhost:8765
