"""
FileForge CLI Entry Point

Allows running the package directly:
    python -m fileforge          # Runs CLI
    python -m fileforge --gui    # Runs GUI
    python -m fileforge.gui      # Also runs GUI
"""

import sys


def main():
    """Main entry point with GUI option."""
    if "--gui" in sys.argv or "-g" in sys.argv:
        # Remove the gui flag from argv
        sys.argv = [arg for arg in sys.argv if arg not in ("--gui", "-g")]
        from fileforge.gui import main as gui_main
        gui_main()
    else:
        from fileforge.cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()
