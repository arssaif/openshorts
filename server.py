#!/usr/bin/env python3
"""
Server runner for GTA 6 Viral Clipper UI.
"""
import sys
import argparse
import uvicorn
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description="Start GTA 6 Viral Clipper Local Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("🌴 GTA 6 VIRAL CLIPPER AI - LOCALHOST DASHBOARD 🌴")
    print(f"👉 Open in browser: http://localhost:{args.port}")
    print(f"👉 Local network:   http://{args.host}:{args.port}")
    print("=" * 65 + "\n")

    uvicorn.run("backend.app:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()

