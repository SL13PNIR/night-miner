# Test script for NIGHT Token Miner

Write-Host "Testing NIGHT Token Miner..." -ForegroundColor Green

# Run unit tests
Write-Host "`nRunning unit tests..." -ForegroundColor Yellow
cargo test --release

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "`n✗ Some tests failed!" -ForegroundColor Red
    exit 1
}

# Run clippy for linting
Write-Host "`nRunning clippy linter..." -ForegroundColor Yellow
cargo clippy --release -- -D warnings

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ No clippy warnings!" -ForegroundColor Green
} else {
    Write-Host "`n⚠ Clippy found issues (see above)" -ForegroundColor Yellow
}

# Format check
Write-Host "`nChecking code formatting..." -ForegroundColor Yellow
cargo fmt -- --check

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Code is properly formatted!" -ForegroundColor Green
} else {
    Write-Host "`n⚠ Code needs formatting. Run: cargo fmt" -ForegroundColor Yellow
}

Write-Host "`nAll checks complete!" -ForegroundColor Green
