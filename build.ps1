# Build script for NIGHT Token Miner

Write-Host "Building NIGHT Token Miner..." -ForegroundColor Green

# Clean previous build
Write-Host "`nCleaning previous build..." -ForegroundColor Yellow
cargo clean

# Build in release mode with optimizations
Write-Host "`nBuilding in release mode..." -ForegroundColor Yellow
cargo build --release

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Build successful!" -ForegroundColor Green
    Write-Host "`nBinary location: target\release\night-miner.exe" -ForegroundColor Cyan
    
    # Get binary size
    $size = (Get-Item "target\release\night-miner.exe").Length / 1MB
    Write-Host "Binary size: $([math]::Round($size, 2)) MB" -ForegroundColor Cyan
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Set up your wallet configuration: Copy-Item wallet.example.json wallet.json"
    Write-Host "2. Get terms and conditions: .\target\release\night-miner.exe tandc"
    Write-Host "3. Register your address: .\target\release\night-miner.exe register --wallet wallet.json --signature YOUR_SIGNATURE"
    Write-Host "4. Start mining: .\target\release\night-miner.exe mine --wallet wallet.json"
    Write-Host "`nSee QUICKSTART.md for detailed instructions." -ForegroundColor Cyan
} else {
    Write-Host "`n✗ Build failed!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Red
    exit 1
}
