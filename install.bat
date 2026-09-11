@echo off
python -m pip install -e .
python -c from ffdl.protocol import register_windows_protocol; register_windows_protocol()
echo [SUCCESS] FFDL Installed and registered!
pause
