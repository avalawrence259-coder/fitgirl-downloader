"""
ffdl.__main__ - Module Executable Entrypoint
"""

import sys
from ffdl.cli import main

if __name__ == "__main__":
    is_protocol = any(arg.lower().startswith("ffdl://") or arg.lower().startswith("ffdl:") for arg in sys.argv[1:])
    try:
        main()
    except SystemExit as se:
        if se.code not in (0, None) and is_protocol:
            print("\nWindow will remain open for review. Press Enter to close this window...")
            try:
                input()
            except Exception:
                pass
        raise
    except Exception as exc:
        print(f"\n[FFDL Critical Error] {exc}")
        import traceback
        traceback.print_exc()
        if is_protocol:
            print("\nWindow will remain open for review. Press Enter to close this window...")
            try:
                input()
            except Exception:
                pass
        sys.exit(1)

