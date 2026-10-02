import uvicorn
import webbrowser
import threading
import time
import os

def open_browser(port):
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{port}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("=" * 65)
    print("🚀 PortfolioPulse - Yahoo Finance Portfolio & Holding Analyzer")
    print(f"📡 Server running at: http://127.0.0.1:{port}")
    print("=" * 65)

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)

