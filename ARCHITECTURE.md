# NIGHT Token Miner - Technical Architecture

## Overview

This is a high-performance, production-ready miner for the NIGHT Token Scavenger Mine program. It implements the complete API specification and optimizes mining performance through efficient multi-threading and resource management.

**Key Features:**
- **AutoMine Mode**: Automated multi-address management (recommended)
- **Manual Mode**: Single-address mining with external wallet management
- **AshMaize Algorithm**: CPU-only, memory-hard (1GB ROM), ASIC/GPU-resistant
- **Performance**: ~180× faster than browser miner
- **Persistent State**: Tracks submissions across restarts

## Project Structure

```
night-miner/
├── src/
│   ├── main.rs              # CLI entry point, AutoMine command, mining loop
│   ├── config.rs            # Configuration management
│   ├── api/
│   │   ├── mod.rs           # API module exports
│   │   ├── models.rs        # Data structures for API responses
│   │   └── client.rs        # HTTP client for Scavenger Mine API
│   ├── wallet/
│   │   └── mod.rs           # Wallet configuration and address management
│   ├── miner/
│   │   ├── mod.rs           # Mining module exports
│   │   └── engine.rs        # Multi-threaded AshMaize mining engine
│   └── coordinator/
│       └── mod.rs           # Mining coordinator (orchestration)
├── auto-mine-wallet/        # Created during AutoMine operation
│   ├── wallet.json          # Address list + submission tracking
│   ├── wallet-stake.skey    # Shared stake key for all addresses
│   ├── wallet-stake.vkey    # Shared stake verification key
│   ├── addr_0.skey          # Payment signing key (address 0)
│   ├── addr_0.vkey          # Payment verification key (address 0)
│   ├── addr_0.addr          # Cardano address (address 0)
│   └── ...                  # Additional addresses (100+ typical)
├── Cargo.toml               # Rust dependencies and build config
├── README.md                # Comprehensive documentation
├── TROUBLESHOOTING.md       # Troubleshooting guide
├── ARCHITECTURE.md          # This file
├── config.example.toml      # Example configuration (manual mode)
├── wallet.example.json      # Example wallet configuration (manual mode)
├── build.ps1                # Build script
└── test.ps1                 # Test script
```

## Architecture Principles

### 1. Separation of Concerns

Each module has a single, well-defined responsibility:

- **API Module**: Handles all HTTP communication with the Scavenger Mine service
- **Wallet Module**: Manages wallet configuration, address creation, and submission tracking
- **Miner Module**: Implements the core mining algorithm with AshMaize
- **Coordinator Module**: Orchestrates the mining process (timing, submission, stats)
- **Config Module**: Manages application configuration
- **AutoMine System**: Automated multi-address lifecycle management (in main.rs)

### 2. Performance Optimization

**Multi-threading Strategy:**
- Uses crossbeam channels for efficient inter-thread communication
- Each thread searches a different nonce space (thread_id-based partitioning)
- Lock-free atomic operations for shared state
- Minimal synchronization overhead

**Memory Management:**
- AshMaize ROM initialized once per challenge (~1GB)
- Shared Arc<Rom> across threads (zero-copy)
- Efficient preimage construction without allocations in hot path

**Hash Rate Optimization:**
- Release build with full optimization (opt-level = 3)
- Link-time optimization (LTO) enabled
- Single codegen unit for better inlining
- Minimal logging in mining hot path

### 3. Robustness

**Error Handling:**
- Comprehensive error types using `anyhow` and `thiserror`
- Graceful degradation on network errors
- Automatic retries for transient failures
- No panics in production code paths

**Resource Management:**
- Clean shutdown on Ctrl+C
- Proper thread cleanup
- No resource leaks

### 4. Maintainability

**Code Organization:**
- Clear module boundaries
- Documented public APIs
- Comprehensive unit tests
- Type safety throughout

**Configuration:**
- Externalized configuration
- Sensible defaults
- CLI overrides
- Validation before execution

## Data Flow

### AutoMine Mode (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                           │
│                  (CLI: night-miner auto-mine)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      AutoMine System                         │
│  - Load/create auto-mine-wallet/wallet.json                 │
│  - Create/load addresses (Cardano CLI)                       │
│  - Track challenge submissions (persistent HashMap)          │
│  - Automatic address rotation per challenge                  │
│  - Create new addresses when all are used                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infinite Mining Loop                       │
│  1. Fetch current challenge from API                         │
│  2. Initialize ROM (~1.5s per challenge)                     │
│  3. Select next unused address for this challenge            │
│  4. Mine until solution found (multi-threaded)               │
│  5. Submit solution to API (with retries)                    │
│  6. Mark address as used for this challenge                  │
│  7. Save state to wallet.json                                │
│  8. Repeat (create new address if all used)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│      API Client          │  │    Mining Engine         │
│  - HTTP requests         │  │  - ROM initialization    │
│  - JSON serialization    │  │  - Thread spawning       │
│  - Error handling        │  │  - Nonce search          │
│  - Infinite retries      │  │  - Difficulty checking   │
│  - Exponential backoff   │  │  - Progress monitoring   │
└──────────────────────────┘  └──────────────────────────┘
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                      ┌───────────────┐   ┌───────────────┐
                      │ Worker Thread │   │ Worker Thread │
                      │  - Search     │   │  - Search     │
                      │  - Hash       │   │  - Hash       │
                      │  - Check      │   │  - Check      │
                      └───────────────┘   └───────────────┘
```

### Manual Mode

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                           │
│            (CLI args, config file, wallet file)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Main Entry Point                          │
│  - Parse CLI arguments                                       │
│  - Load configuration                                        │
│  - Initialize logging                                        │
│  - Dispatch to command handler                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Mining Coordinator                          │
│  - Fetch challenges every hour                               │
│  - Initialize ROM per challenge                              │
│  - Invoke mining engine                                      │
│  - Submit solutions                                          │
│  - Track statistics                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│      API Client          │  │    Mining Engine         │
│  - HTTP requests         │  │  - ROM initialization    │
│  - JSON serialization    │  │  - Thread spawning       │
│  - Error handling        │  │  - Nonce search          │
│  - Rate limiting         │  │  - Difficulty checking   │
└──────────────────────────┘  │  - Progress monitoring   │
                              └──────────────────────────┘
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                      ┌───────────────┐   ┌───────────────┐
                      │ Worker Thread │   │ Worker Thread │
                      │  - Search     │   │  - Search     │
                      │  - Hash       │   │  - Hash       │
                      │  - Check      │   │  - Check      │
                      └───────────────┘   └───────────────┘
```

## Key Algorithms

### Mining Algorithm

The mining process implements the specification exactly:

1. **ROM Initialization**: 
   ```rust
   Rom::new(&no_pre_mine, TwoStep, 1GB)
   ```
   - Uses challenge-specific `no_pre_mine` value
   - 1GB ROM size as specified
   - Two-step generation with 16MB pre-size

2. **Preimage Construction**:
   ```
   preimage = nonce + address + challenge_id + difficulty + 
              no_pre_mine + latest_submission + no_pre_mine_hour
   ```
   - All fields concatenated as strings
   - Nonce is 16 hex characters (8 bytes)

3. **Hashing**:
   ```rust
   hash(&preimage, &rom, 8, 256)
   ```
   - 8 loops, 256 instructions per loop
   - Returns 64-byte hash

4. **Difficulty Check**:
   ```rust
   (hash_value | target) == target
   ```
   - Compares first 4 bytes of hash as u32 (big-endian)
   - Checks that all bits in hash are a subset of bits in target
   - Matches the website's exact implementation

### Thread Partitioning

Each thread searches a unique nonce space:

```rust
thread_start = thread_id << 56  // Top 8 bits identify thread
thread_step = 1                  // Sequential search
```

This ensures no duplicate work across threads while maintaining cache locality.

### Progress Monitoring

- Atomic counters for thread-safe updates
- Periodic aggregation (every 1000 hashes)
- Real-time hash rate calculation
- Non-blocking progress display

## API Integration

### Endpoints Implemented

All Scavenger Mine API endpoints are fully implemented:

1. **GET /TandC**: Fetch terms and conditions
2. **POST /register**: Register wallet address
3. **GET /challenge**: Fetch current challenge
4. **POST /solution**: Submit solution
5. **POST /donate_to**: Consolidate solutions
6. **GET /work_to_star_rate**: Fetch earnings rates

### Error Handling

The API client handles all error cases:
- Network timeouts
- Invalid responses
- Rate limiting
- Server errors
- Validation failures

Errors are logged and mining continues where possible.

## Configuration System

### Hierarchy

1. Default values (sensible defaults)
2. Configuration file (persistent settings)
3. CLI arguments (one-time overrides)

### Settings

| Setting | Default | Description |
|---------|---------|-------------|
| threads | CPU count | Number of mining threads |
| challenge_timeout_minutes | 55 | Timeout per challenge |
| wallet_config_path | wallet.json | Path to wallet config |
| show_progress | true | Show progress bar |
| log_level | info | Logging verbosity |

## AutoMine Architecture

### Address Management

**Wallet Structure:**
- **Shared Stake Key**: One `wallet-stake.skey` for all addresses
- **Individual Payment Keys**: Each address has unique `addr_N.skey`
- All addresses belong to same wallet (same stake key)

**Address Lifecycle:**
1. **Creation**: Via Cardano CLI when starting or when all addresses used
2. **Registration**: Automatic API registration for new addresses
3. **Rotation**: Select next unused address per challenge
4. **Reuse**: Addresses can be reused across different challenges

### Challenge Submission Tracking

**Data Structure:**
```rust
{
  "addresses": [
    {"index": 0, "address": "addr_test1...", "staking_pubkey": "..."},
    {"index": 1, "address": "addr_test1...", "staking_pubkey": "..."},
    // ... 100+ addresses typical
  ],
  "challenge_submissions": {
    "**D02C24": [0, 1, 2, 15, 23, ...],  // Address indices that submitted
    "**D02C23": [0, 1, 2, 3, 4, ...],
    // ... previous challenges
  }
}
```

**Constraints:**
- Each address limited to **1 solution per challenge** (API constraint)
- HashMap tracks which address indices submitted for each challenge ID
- New addresses created when all existing addresses have submitted
- Challenge IDs reset tracking per new challenge

### Persistence & State Management

**wallet.json Updates:**
- Saved after every solution submission
- Tracks challenge_submissions HashMap persistently
- Survives restarts - miner resumes where it left off
- Incremental backup critical (new addresses created on-the-fly)

**Cardano CLI Integration:**
- Searches 3 locations: PATH, ./bin/cardano-cli.exe, ./bin/cardano-cli
- Provides install instructions if not found
- Creates payment keys + verification keys + addresses
- Only needed for AutoMine (not for mining algorithm)

### Time Management

**Previous Implementation (Removed):**
- Used to check countdown timer (300s → 120s → 30s thresholds)
- Would stop creating addresses if "not enough time"

**Current Implementation:**
- **No time-based restrictions** - countdown timer unreliable
- Challenges don't start exactly at 0:00 (can be late)
- Creates new addresses immediately when all are used
- Continues mining until API reports challenge transition
- More aggressive and efficient approach

## Security Considerations

### Private Key Management (AutoMine)

- **Stores private keys locally** in `auto-mine-wallet/`
- Keys required for Cardano transaction signing (when claiming rewards)
- Critical: Backup `auto-mine-wallet/` directory regularly
- All addresses use shared stake key (single wallet)

### Private Key Management (Manual Mode)

- **Never stores private keys**
- Requires external signing via cardano-cli or wallet
- Only stores public information (address, pubkey)

### Message Signing

- Implements CIP-8/30 standard
- Signature verification before use
- Proper COSE_Sign1 structure validation

### Network Security

- HTTPS only
- Certificate validation
- Reasonable timeouts
- No credential caching
- Infinite retry loops with exponential backoff

## Testing Strategy

### Unit Tests

- Configuration validation
- Difficulty parsing and checking
- Preimage construction
- Time calculations
- Message formatting

### Integration Tests

- API client against live endpoints (when appropriate)
- End-to-end mining cycle (with test data)

### Performance Tests

- Hash rate benchmarks
- Thread scaling efficiency
- Memory usage profiling

## Deployment

### Build Process

```powershell
cargo build --release
```

Produces optimized binary with:
- Full optimization
- LTO enabled
- Debug symbols stripped
- ~5-10 MB binary size
- AshMaize dependency automatically fetched from GitHub

### System Requirements

**Required:**
- **OS**: Windows, Linux, macOS
- **RAM**: 2+ GB free (for ROM)
- **CPU**: Any modern processor (more cores = better)
- **Disk**: ~50 MB for binary + logs + wallet files
- **Network**: Stable internet connection

**Optional (AutoMine only):**
- **Cardano CLI**: For address creation (auto-detected or install prompted)

### Runtime Behavior

**AutoMine Mode:**
- **Startup**: ~1.5s per challenge for ROM initialization
- **Memory**: ~1.2 GB steady-state (ROM + program)
- **CPU**: 100% utilization (all available threads)
- **Network**: ~1 KB/min (periodic API calls with infinite retries)
- **Disk I/O**: wallet.json updated after each solution submission
- **Persistence**: Survives restarts - resumes from last state

**Manual Mode:**
- **Startup**: ~15-30s for ROM initialization
- **Memory**: ~1.2 GB steady-state
- **CPU**: 100% utilization (configurable)
- **Network**: ~1 KB/min (periodic API calls)

## Monitoring and Observability

### Logging Levels

- **ERROR**: Critical failures requiring attention
- **WARN**: Recoverable issues (timeouts, retries)
- **INFO**: Normal operation (challenges, solutions, stats)
- **DEBUG**: Detailed operation (thread lifecycle, etc.)
- **TRACE**: Very verbose (hash attempts, etc.)

### Metrics Tracked

- Challenges attempted
- Solutions found
- Solutions submitted
- Success rate
- Total STAR earned
- Hash rate per thread
- Average time per solution

### Progress Display

Real-time progress bar shows:
- Elapsed time
- Total hashes computed
- Current hash rate
- Status messages

## Performance Characteristics

### Expected Hash Rates

Based on CPU architecture (AshMaize is CPU-only):

| CPU Type | Cores | Expected Rate |
|----------|-------|---------------|
| Mobile i5 | 4 | 50-150 H/s |
| Desktop i7 | 8 | 200-400 H/s |
| **i9-11900H** | **16 threads** | **~9,000-9,500 H/s** |
| Ryzen 5950X | 16 | 500-1000 H/s |
| Threadripper | 32+ | 1000+ H/s |

**Performance vs Browser Miner:**
- This miner: ~9,500 H/s (example i9-11900H)
- Browser miner: ~52 H/s (same hardware)
- **180× performance improvement**

**Solution Rate:**
- ~3 solutions per minute
- ~4,320 solutions per day (with 100+ addresses in AutoMine)

### Difficulty Analysis

Difficulty varies per challenge. Time to solution:

| Difficulty | Zero Bits | Avg Time @ 1000 H/s |
|------------|-----------|---------------------|
| 0000FFFF | 16 | ~65 seconds |
| 00007FFF | 17 | ~130 seconds |
| 00003FFF | 18 | ~260 seconds |
| 00001FFF | 19 | ~520 seconds |

### Resource Usage

- **CPU**: 100% of configured threads
- **Memory**: ~1.2 GB (ROM) + ~100 MB (program)
- **Network**: Minimal (~1 KB/min)
- **Disk**: Minimal (logs only)

## Troubleshooting

See TROUBLESHOOTING.md for common issues and solutions.

## Known Issues & Limitations

### API Limitations (November 2025)

**donate_to Endpoint Broken:**
- Cannot consolidate solutions to single address
- Users must claim rewards on **each address individually**
- With 100+ addresses in AutoMine, claiming will be tedious
- Workaround: Import `.skey` files into Eternl wallet for easier management

### Challenge Timer Accuracy

- Countdown timer on website is not accurate
- Challenges don't transition exactly at 0:00 (can be late)
- Miner no longer relies on countdown timer
- Continues mining until API reports challenge transition

## Future Enhancements

**Potential Improvements:**
1. Automated claiming system (when donate_to fixed)
2. GUI for easier wallet management
3. Cloud deployment support
4. Multi-machine coordination
5. Enhanced statistics dashboard
6. Automated backup system

## Acknowledgments

- **AshMaize**: ASIC-resistant hash algorithm by Input Output
  - Repository: https://github.com/input-output-hk/ce-ashmaize
  - Algorithm: CPU-only, memory-hard (1GB ROM), ASIC/GPU-resistant
  - Specifications: 8 hash loops, 256 instructions, 16MB pre-size, 4 mixing numbers
- **Midnight Network**: NIGHT token and Scavenger Mine program
- **Rust Community**: Excellent tooling and libraries
- **Cardano CLI**: Address generation and key management
