@echo off
echo === VoxPrompt Setup ===
echo.

:: Create venv if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate venv
call .venv\Scripts\activate.bat

:: Install PyTorch with CUDA first
echo Installing PyTorch with CUDA support...
pip install torch --index-url https://download.pytorch.org/whl/cu128

:: Install remaining dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo === Setup complete ===
echo.
echo To run VoxPrompt:
echo   .venv\Scripts\activate.bat
echo   python -m voxprompt.main
echo.
pause
