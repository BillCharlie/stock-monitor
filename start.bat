@echo off
echo ============================================
echo  台灣/美國股市監控系統
echo  單一端口: http://localhost:8765
echo ============================================
echo.

python --version >nul 2>&1 || (echo [ERROR] 找不到 Python & pause & exit /b 1)
node --version   >nul 2>&1 || (echo [ERROR] 找不到 Node.js & pause & exit /b 1)

if not exist "backend\venv" (
    echo [1/4] 建立 Python 虛擬環境...
    python -m venv backend\venv
)

echo [2/4] 安裝後端套件...
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q

if not exist "frontend\node_modules" (
    echo [3/4] 安裝前端套件...
    cd frontend && npm install && cd ..
)

echo [4/4] 建置前端並啟動...
echo.
echo  前端建置中 (--watch 模式，檔案變更自動重建)
echo  後端 API + 前端 SPA: http://localhost:8765
echo.
echo  修改前端後請手動重新整理瀏覽器 (F5)
echo  按 Ctrl+C 停止
echo.

:: Build frontend first (blocking), then watch
cd frontend
npm run build 2>nul
cd ..

:: Start backend (serves static + API)
start "Stock Monitor" cmd /k "cd backend && ..\backend\venv\Scripts\activate.bat && python -m uvicorn main:app --reload --port 8765 --host 0.0.0.0"

:: Watch frontend for changes
cd frontend
npm run dev

pause
