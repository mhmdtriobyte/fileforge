#!/usr/bin/env python3
"""
FileForge Launcher Script
Starts both the FastAPI backend and React frontend development servers.
"""

import subprocess
import sys
import os
import signal
import time
import platform
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print the FileForge banner."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ███████╗██╗██╗     ███████╗███████╗ ██████╗ ██████╗ ███████╗   ║
    ║   ██╔════╝██║██║     ██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝   ║
    ║   █████╗  ██║██║     █████╗  █████╗  ██║   ██║██████╔╝█████╗     ║
    ║   ██╔══╝  ██║██║     ██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██╔══╝     ║
    ║   ██║     ██║███████╗███████╗██║     ╚██████╔╝██║  ██║███████╗   ║
    ║   ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝   ║
    ║                                                           ║
    ║              Modern File Converter Web App                ║
    ╚═══════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)

def check_dependencies():
    """Check if required dependencies are available."""
    print(f"{Colors.YELLOW}Checking dependencies...{Colors.END}")

    # Check Python packages
    try:
        import fastapi
        import uvicorn
        import PIL
        import pypdf
        import pandas
        print(f"  {Colors.GREEN}✓{Colors.END} Python packages installed")
    except ImportError as e:
        print(f"  {Colors.RED}✗{Colors.END} Missing Python package: {e.name}")
        print(f"    Run: pip install -r requirements.txt")
        return False

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            shell=platform.system() == "Windows"
        )
        if result.returncode == 0:
            print(f"  {Colors.GREEN}✓{Colors.END} Node.js {result.stdout.strip()}")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print(f"  {Colors.RED}✗{Colors.END} Node.js not found")
        print(f"    Install Node.js from https://nodejs.org/")
        return False

    # Check npm
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            shell=platform.system() == "Windows"
        )
        if result.returncode == 0:
            print(f"  {Colors.GREEN}✓{Colors.END} npm {result.stdout.strip()}")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print(f"  {Colors.RED}✗{Colors.END} npm not found")
        return False

    return True

def install_frontend_deps(frontend_path: Path):
    """Install frontend dependencies if node_modules doesn't exist."""
    node_modules = frontend_path / "node_modules"

    if not node_modules.exists():
        print(f"\n{Colors.YELLOW}Installing frontend dependencies...{Colors.END}")
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_path,
            shell=platform.system() == "Windows"
        )
        if result.returncode != 0:
            print(f"{Colors.RED}Failed to install frontend dependencies{Colors.END}")
            return False
        print(f"{Colors.GREEN}Frontend dependencies installed!{Colors.END}")

    return True

def start_servers():
    """Start both backend and frontend servers."""
    base_path = Path(__file__).parent
    backend_path = base_path / "backend"
    frontend_path = base_path / "frontend"

    processes = []

    try:
        # Start backend server
        print(f"\n{Colors.BLUE}Starting backend server on http://localhost:8000{Colors.END}")
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_path,
            shell=False
        )
        processes.append(("Backend", backend_process))

        # Give backend a moment to start
        time.sleep(2)

        # Start frontend server
        print(f"{Colors.BLUE}Starting frontend server on http://localhost:3000{Colors.END}")

        # Use npm.cmd on Windows, npm on Unix
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_path,
            shell=False
        )
        processes.append(("Frontend", frontend_process))

        print(f"\n{Colors.GREEN}{Colors.BOLD}FileForge is running!{Colors.END}")
        print(f"""
{Colors.CYAN}╭─────────────────────────────────────────────────╮
│                                                 │
│   Frontend:  http://localhost:3000              │
│   Backend:   http://localhost:8000              │
│   API Docs:  http://localhost:8000/docs         │
│                                                 │
│   Press Ctrl+C to stop all servers              │
│                                                 │
╰─────────────────────────────────────────────────╯{Colors.END}
""")

        # Wait for processes
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    print(f"{Colors.RED}{name} server stopped unexpectedly{Colors.END}")
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Shutting down servers...{Colors.END}")
        for name, process in processes:
            try:
                if platform.system() == "Windows":
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                print(f"  {Colors.GREEN}✓{Colors.END} {name} stopped")
            except Exception as e:
                process.kill()
                print(f"  {Colors.YELLOW}!{Colors.END} {name} force killed")

        print(f"\n{Colors.GREEN}Goodbye!{Colors.END}")

def main():
    """Main entry point."""
    print_banner()

    base_path = Path(__file__).parent
    frontend_path = base_path / "frontend"

    # Check dependencies
    if not check_dependencies():
        print(f"\n{Colors.RED}Please install missing dependencies and try again.{Colors.END}")
        sys.exit(1)

    # Install frontend deps if needed
    if not install_frontend_deps(frontend_path):
        sys.exit(1)

    # Start servers
    start_servers()

if __name__ == "__main__":
    main()
