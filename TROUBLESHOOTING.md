# Troubleshooting Guide

Common issues and their solutions.

## Build Issues

### "cargo: command not found"

**Problem**: Rust is not installed or not in PATH

**Solution**:
1. Install Rust from https://rustup.rs
2. Restart PowerShell
3. Verify: `cargo --version`

### "error: linker `link.exe` not found"

**Problem**: Missing C++ build tools (Windows)

**Solution**:
- Install Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
- Or install Visual Studio Community with "Desktop development with C++"
- Restart terminal after installation

### "failed to load source for dependency `ashmaize`"

**Problem**: AshMaize library not found in expected location

**Solution**:
1. Verify directory structure:
   ```
   your-project-dir/
   ├── ce-ashmaize-master/
   └── night-miner/
   ```
2. Check path in `Cargo.toml`: `ashmaize = { path = "../ce-ashmaize-master" }`
3. Adjust if your structure is different

### "error: could not compile `night-miner`"

**Problem**: Compilation error in code

**Solution**:
1. Clean and rebuild: `cargo clean ; cargo build --release`
2. Update dependencies: `cargo update`
3. Check Rust version: `rustc --version` (should be 1.70+)

## Configuration Issues

### "Failed to read wallet configuration file"

**Problem**: wallet.json not found or invalid

**Solution**:
1. Create from template: `Copy-Item wallet.example.json wallet.json`
2. Verify JSON is valid (use online JSON validator)
3. Check file path: `Test-Path wallet.json`

### "Failed to parse wallet configuration"

**Problem**: Invalid JSON syntax in wallet.json

**Solution**:
1. Check for:
   - Missing commas
   - Extra commas
   - Unclosed quotes
   - Unclosed braces
2. Use JSON validator: https://jsonlint.com
3. Compare with `wallet.example.json`

### "Failed to read configuration file"

**Problem**: config.toml syntax error

**Solution**:
1. Check TOML syntax
2. Verify string values are quoted: `log_level = "info"`
3. Compare with `config.example.toml`
4. Try without config file first (uses defaults)

## Registration Issues

### "Address is not registered"

**Problem**: Must register before mining

**Solution**:
1. Get T&C: `.\target\release\night-miner.exe tandc`
2. Sign the message with cardano-cli or wallet
3. Register: `.\target\release\night-miner.exe register --wallet wallet.json --signature YOUR_SIG`
4. Verify you see "Registration successful!"

### "CIP-30 signature verification failed"

**Problem**: Invalid or incorrectly formatted signature

**Solution**:
1. Ensure signature is for the EXACT message from `/tandc`
2. Signature must be hex-encoded COSE_Sign1
3. Use correct address that matches wallet.json
4. Verify with: https://verifycardanomessage.cardanofoundation.org/

### "Wrong network: expected preprod, got mainnet"

**Problem**: Using wrong Cardano network

**Solution**:
- The Scavenger Mine uses mainnet
- Ensure your address starts with `addr1` (not `addr_test1`)
- Use mainnet keys and signatures

### "Invalid pubkey format"

**Problem**: Public key is not in correct format

**Solution**:
1. Must be 64-character hex string (short form)
2. Not the long form from wallets
3. Extract from signing key if needed
4. Remove any "0x" prefix

## Mining Issues

### "Failed to initialize ROM"

**Problem**: Not enough RAM

**Solution**:
1. Close other applications
2. Check available RAM: `Get-ComputerInfo | Select-Object OsTotalVisibleMemorySize`
3. Need at least 2GB free
4. Consider restarting computer

### "Solution does not meet difficulty"

**Problem**: This is NORMAL - not actually an error

**Explanation**:
- The miner tries many nonces
- Most don't meet difficulty
- Miner keeps trying automatically
- Eventually finds a valid nonce

### Low Hash Rate

**Problem**: Slower than expected mining

**Solution**:
1. Ensure built with `--release`: `cargo build --release`
2. Close CPU-intensive applications
3. Check CPU temperature (thermal throttling)
4. Try adjusting thread count: `--threads 8`
5. Verify CPU governor is on "performance" mode

### High CPU Usage

**Problem**: 100% CPU usage

**Explanation**:
- This is EXPECTED behavior
- Mining is CPU-intensive
- Uses all configured threads

**If problematic**:
- Reduce threads: `--threads 4`
- Set CPU affinity (advanced)
- Use process priority (Task Manager)

### "Mining timed out for challenge"

**Problem**: Didn't find solution in timeout period

**Explanation**:
- Sometimes difficulty is high
- May not find solution before next challenge
- This is normal

**Solutions**:
- Increase timeout: `--timeout 59`
- Add more threads: `--threads 16`
- Wait for next challenge (automatic)

## Network Issues

### "Connection refused" or "Connection timeout"

**Problem**: Cannot reach API server

**Solution**:
1. Check internet connection
2. Verify API is up: Try in browser: https://scavenger.prod.gd.midnighttge.io/challenge
3. Check firewall settings
4. Try different network
5. Wait and retry (temporary outage)

### "Failed to fetch challenge"

**Problem**: API request failed

**Solution**:
1. Check internet connection
2. Verify mining period has started
3. Wait and retry (miner does this automatically)
4. Check API status

### SSL/TLS Errors

**Problem**: Certificate verification failed

**Solution**:
1. Update Windows
2. Check system time is correct
3. Update root certificates
4. Temporarily disable antivirus (test only)

## Runtime Issues

### "Address already has an active donation"

**Problem**: Already donated to another address

**Solution**:
- Can only donate to one destination
- To undo: Donate to self
- To change: First undo, then donate to new address

### "Challenge not found"

**Problem**: Challenge ID not recognized

**Solution**:
- Fetch current challenge first
- Use exact challenge_id from response
- Ensure mining period is active

### Miner Crashes

**Problem**: Unexpected termination

**Solution**:
1. Run with debug logging: `--log-level debug`
2. Check last log messages
3. Verify sufficient RAM
4. Check disk space for logs
5. Update Rust: `rustup update`

### "Solution submission failed"

**Problem**: Valid solution not accepted

**Solution**:
1. Verify you're registered
2. Check challenge hasn't expired
3. Ensure correct challenge_id
4. Retry (miner may auto-retry)
5. Check for API errors in logs

## Performance Issues

### Slower Than Expected

**Diagnostics**:
```powershell
# Check CPU info
Get-ComputerInfo | Select-Object CsProcessors

# Check running with release build
.\target\release\night-miner.exe --version  # Should be release binary

# Monitor with debug logs
.\target\release\night-miner.exe mine --wallet wallet.json --log-level debug
```

**Solutions**:
1. Ensure release build
2. Close background apps
3. Check CPU throttling
4. Verify cooling
5. Try different thread counts

### Memory Issues

**Problem**: Out of memory errors

**Solution**:
1. Close other applications
2. Increase virtual memory (pagefile)
3. Reduce number of threads
4. Upgrade RAM (if possible)

### Disk Space Issues

**Problem**: No space for logs

**Solution**:
1. Clean up old logs
2. Reduce log level: `--log-level warn`
3. Free up disk space

## Advanced Debugging

### Enable Verbose Logging

```powershell
$env:RUST_LOG="night_miner=trace,ashmaize=debug"
.\target\release\night-miner.exe mine --wallet wallet.json
```

### Capture Full Output

```powershell
.\target\release\night-miner.exe mine --wallet wallet.json 2>&1 | Tee-Object -FilePath mining.log
```

### Test Individual Commands

```powershell
# Test T&C endpoint
.\target\release\night-miner.exe tandc

# Test challenge endpoint
.\target\release\night-miner.exe challenge

# Test rates endpoint
.\target\release\night-miner.exe rates

# Check wallet config
Get-Content wallet.json | ConvertFrom-Json
```

### Verify Dependencies

```powershell
cargo tree | Select-String ashmaize
cargo tree | Select-String tokio
```

## Getting Help

### Before Asking for Help

1. ✅ Check this guide
2. ✅ Read README.md
3. ✅ Check SETUP.md
4. ✅ Run with `--log-level debug`
5. ✅ Verify configuration files
6. ✅ Test individual commands

### When Reporting Issues

Include:
- OS version: `Get-ComputerInfo | Select-Object WindowsVersion`
- Rust version: `rustc --version`
- Full error message
- Command used
- Logs (with `--log-level debug`)
- Configuration (without private keys!)

### Useful Commands for Debugging

```powershell
# System info
Get-ComputerInfo

# Check Rust installation
rustc --version
cargo --version

# Verify project structure
Get-ChildItem -Recurse -Depth 1

# Test build
cargo check

# Clean build
cargo clean
cargo build --release

# Run tests
cargo test --release -- --nocapture
```

## Common Misunderstandings

### "Why is CPU usage so high?"
- **Expected**: Mining uses 100% CPU by design
- **Reduce if needed**: Use `--threads` parameter

### "Why aren't I finding solutions?"
- **Normal**: Difficulty varies, sometimes takes time
- **Keep running**: Miner will eventually find solutions

### "Do I need to run for 21 days straight?"
- **Yes**: For maximum rewards
- **But**: Can stop/start as needed (track your stats)

### "Why doesn't it use my private key?"
- **Security**: External signing is safer
- **Design choice**: Reduces attack surface

### "Can I run multiple instances?"
- **Yes**: Use different wallet configs
- **Consolidate**: Use `donate` command later

## Still Having Issues?

1. Try the example configuration files as-is
2. Test without custom config (uses defaults)
3. Verify ashmaize library is working:
   ```powershell
   cd ..\ce-ashmaize-master
   cargo test
   ```
4. Check Midnight Network documentation
5. Verify API is accessible in browser

## Emergency Fixes

### Nuclear Option: Complete Reset

```powershell
# Remove all build artifacts
cargo clean

# Remove Cargo cache (if needed)
Remove-Item -Recurse -Force "$env:USERPROFILE\.cargo\registry"

# Rebuild from scratch
cargo build --release
```

### Start Fresh

```powershell
# Backup your wallet.json
Copy-Item wallet.json wallet.json.backup

# Remove config
Remove-Item config.toml

# Use defaults
.\target\release\night-miner.exe mine --wallet wallet.json
```

---

If all else fails, ensure you have:
1. ✅ Latest Rust version
2. ✅ Valid wallet.json
3. ✅ Registered address
4. ✅ Built with `--release`
5. ✅ Stable internet
6. ✅ 2GB+ free RAM

Happy mining! 🚀
