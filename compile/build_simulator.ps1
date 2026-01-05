Write-Host "================================================" -ForegroundColor Cyan
Write-Host "LanComm Beltpack Simulator - Build Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
try {
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller not found"
    }
} catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
    Write-Host ""
}
Write-Host "Building Beltpack Simulator..." -ForegroundColor Green
Write-Host ""
pyinstaller --name "LanComm-Simulator" `
    --onefile `
    --windowed `
    --icon=NONE `
    --hidden-import=PyQt6.QtCore `
    --hidden-import=PyQt6.QtGui `
    --hidden-import=PyQt6.QtWidgets `
    --clean `
    beltpack_simulator.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "BUILD FAILED!" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "BUILD SUCCESSFUL!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable location: " -NoNewline
Write-Host "dist\LanComm-Simulator.exe" -ForegroundColor Yellow
Write-Host ""
Write-Host "You can now run the simulator without Python installed!" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
