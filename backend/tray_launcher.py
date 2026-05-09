"""
Windows System Tray Launcher for Stock Monitor
- Right-click tray icon → Start / Stop / Open Browser / Quit
- Can be compiled to .exe with: pyinstaller --onefile --noconsole --icon=icon.ico tray_launcher.py

Usage: python tray_launcher.py
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing tray dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow", "-q"])
    import pystray
    from PIL import Image, ImageDraw

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
VENV_PY   = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
FRONTEND  = os.path.join(BASE_DIR, "..", "frontend")
APP_URL   = "http://localhost:8765"
PORT      = 8765

_backend_proc  = None
_frontend_proc = None
_lock = threading.Lock()


def _make_icon(color: str = "#26A69A") -> Image.Image:
    """Generate a simple chart-like tray icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Dark background circle
    d.ellipse([2, 2, size - 2, size - 2], fill=(20, 20, 20, 230))
    # Simple "rising chart" bars
    bars = [(8, 48, 18, 32), (20, 48, 30, 20), (32, 48, 42, 28), (44, 48, 54, 12)]
    c = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    for bar in bars:
        d.rectangle(bar, fill=c)
    return img


def _is_running() -> bool:
    import socket
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", PORT))
        s.close()
        return True
    except Exception:
        return False


def start_services(icon=None, item=None):
    global _backend_proc, _frontend_proc
    with _lock:
        if _is_running():
            if icon:
                icon.notify("服務已在運行中", "Stock Monitor")
            return

        # 1. Build frontend if needed
        static_index = os.path.join(BASE_DIR, "static", "index.html")
        if not os.path.exists(static_index):
            if icon:
                icon.notify("正在建置前端...", "Stock Monitor")
            npm = "npm.cmd" if sys.platform == "win32" else "npm"
            subprocess.run([npm, "run", "build"], cwd=FRONTEND, shell=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Start uvicorn
        py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
        _backend_proc = subprocess.Popen(
            [py, "-m", "uvicorn", "main:app", "--port", str(PORT), "--host", "0.0.0.0"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for port to open
        for _ in range(20):
            time.sleep(0.5)
            if _is_running():
                break

        if icon:
            icon.icon = _make_icon("#26A69A")
            icon.notify("服務已啟動 ✓", f"開啟 {APP_URL}")


def stop_services(icon=None, item=None):
    global _backend_proc, _frontend_proc
    with _lock:
        if _backend_proc and _backend_proc.poll() is None:
            _backend_proc.terminate()
            _backend_proc = None
        if icon:
            icon.icon = _make_icon("#EF5350")
            icon.notify("服務已停止", "Stock Monitor")


def open_browser(icon=None, item=None):
    webbrowser.open(APP_URL)


def quit_app(icon, item=None):
    stop_services()
    icon.stop()


def main():
    icon_img = _make_icon("#EF5350")  # Red = stopped

    menu = pystray.Menu(
        pystray.MenuItem("▶ 啟動服務",  start_services, default=True),
        pystray.MenuItem("■ 停止服務",  stop_services),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 開啟瀏覽器", open_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("✕ 退出",       quit_app),
    )

    icon = pystray.Icon(
        name="StockMonitor",
        icon=icon_img,
        title="股市監控系統",
        menu=menu,
    )

    # Auto-start on launch
    threading.Thread(target=start_services, args=(icon,), daemon=True).start()

    icon.run()


if __name__ == "__main__":
    main()
