#!/usr/bin/env python3
"""
Start Backend + Frontend locally for development

Usage:
    python scripts/start_local.py

This script:
1. Checks prerequisites (Python packages, Node modules)
2. Starts FastAPI backend (port 8000)
3. Waits for backend to be ready
4. Starts Next.js frontend (port 3000)
5. Opens browser automatically
6. Handles graceful shutdown on Ctrl+C

Requirements:
    - Python 3.8+ with dependencies installed
    - Node.js 18+ with npm
    - .env file with GROQ_API_KEY (optional but recommended)
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional
import signal
import atexit

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# Global process handles for cleanup
backend_process: Optional[subprocess.Popen] = None
frontend_process: Optional[subprocess.Popen] = None


def print_banner():
    """Print startup banner."""
    print("=" * 60)
    print("  MF FAQ Assistant - Local Development Server")
    print("=" * 60)
    print()


def check_prerequisites():
    """Check that all prerequisites are met."""
    project_root = Path(__file__).parent.parent
    
    # Check .env file
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found")
        if env_example.exists():
            print("   Copy .env.example to .env and add your GROQ_API_KEY")
        print()
    
    # Check if backend dependencies installed
    try:
        import fastapi
        import chromadb
        print("✅ Python dependencies installed")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if frontend dependencies installed
    web_dir = project_root / "web"
    node_modules = web_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing frontend dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=web_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to install frontend dependencies: {result.stderr}")
            sys.exit(1)
        print("✅ Frontend dependencies installed")
    else:
        print("✅ Frontend dependencies already installed")
    
    print()


def wait_for_backend(url: str, timeout: int = 30) -> bool:
    """Wait for backend to be ready."""
    import urllib.request
    import urllib.error
    
    start_time = time.time()
    print(f"⏳ Waiting for backend at {url}...")
    
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            print(f"✅ Backend is ready!")
            return True
        except urllib.error.HTTPError:
            # Server is up but returned error (might be 404, etc)
            print(f"✅ Backend is responding!")
            return True
        except Exception:
            time.sleep(1)
            print("   Still waiting...")
    
    print(f"⚠️  Backend didn't respond within {timeout}s, continuing anyway...")
    return False


def start_backend() -> subprocess.Popen:
    """Start the FastAPI backend."""
    project_root = Path(__file__).parent.parent
    
    print(f"🚀 Starting Backend (FastAPI) on port {BACKEND_PORT}...")
    print(f"   URL: {BACKEND_URL}")
    print(f"   Docs: {BACKEND_URL}/docs")
    print()
    
    # Use creationflags on Windows to create new process group
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    
    process = subprocess.Popen(
        [sys.executable, "-m", "runtime.phase_9_api"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **kwargs
    )
    
    return process


def start_frontend() -> subprocess.Popen:
    """Start the Next.js frontend."""
    project_root = Path(__file__).parent.parent
    web_dir = project_root / "web"
    
    print(f"🚀 Starting Frontend (Next.js) on port {FRONTEND_PORT}...")
    print(f"   URL: {FRONTEND_URL}")
    print()
    
    # Use creationflags on Windows to create new process group
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **kwargs
    )
    
    return process


def open_browser(url: str, delay: int = 3):
    """Open browser after delay."""
    def _open():
        time.sleep(delay)
        print(f"🌐 Opening browser: {url}")
        webbrowser.open(url)
    
    import threading
    threading.Thread(target=_open, daemon=True).start()


def cleanup():
    """Clean up processes on exit."""
    print("\n🛑 Shutting down services...")
    
    if backend_process:
        print("   Stopping backend...")
        if sys.platform == "win32":
            backend_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            backend_process.terminate()
        backend_process.wait(timeout=5)
    
    if frontend_process:
        print("   Stopping frontend...")
        frontend_process.terminate()
        frontend_process.wait(timeout=5)
    
    print("✅ All services stopped")


def print_status():
    """Print running services status."""
    print()
    print("=" * 60)
    print("  All services are running!")
    print("=" * 60)
    print()
    print(f"  🖥️  Frontend:  {FRONTEND_URL}")
    print(f"  ⚙️  Backend:   {BACKEND_URL}")
    print(f"  📚 API Docs:  {BACKEND_URL}/docs")
    print(f"  💚 Health:    {BACKEND_URL}/health")
    print()
    print("  Press Ctrl+C to stop all services")
    print("=" * 60)
    print()


def stream_output(process: subprocess.Popen, prefix: str):
    """Stream process output with prefix."""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{prefix}] {line.rstrip()}")
    except Exception:
        pass


def main():
    """Main entry point."""
    global backend_process, frontend_process
    
    print_banner()
    
    # Check prerequisites
    check_prerequisites()
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    try:
        # Start backend
        backend_process = start_backend()
        
        # Wait for backend to be ready
        wait_for_backend(f"{BACKEND_URL}/health", timeout=15)
        print()
        
        # Start frontend
        frontend_process = start_frontend()
        
        # Give frontend a moment to start
        time.sleep(3)
        
        # Open browser
        open_browser(FRONTEND_URL, delay=2)
        
        # Print status
        print_status()
        
        # Keep running until interrupted
        try:
            while True:
                # Check if processes are still running
                if backend_process.poll() is not None:
                    print("❌ Backend process exited unexpectedly")
                    break
                if frontend_process.poll() is not None:
                    print("❌ Frontend process exited unexpectedly")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Received interrupt signal")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup()


if __name__ == "__main__":
    main()
