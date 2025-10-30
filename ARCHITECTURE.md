# NIGHT Token Miner - Technical Architecture

## Overview

This is a high-performance, production-ready miner for the NIGHT Token Scavenger Mine program. It implements the complete API specification and optimizes mining performance through efficient multi-threading and resource management.

## Project Structure

```
night-miner/
├── src/
│   ├── main.rs              # CLI entry point and command handling
│   ├── config.rs            # Configuration management
│   ├── api/
│   │   ├── mod.rs           # API module exports
│   │   ├── models.rs        # Data structures for API responses
│   │   └── client.rs        # HTTP client for Scavenger Mine API
│   ├── wallet/
│   │   └── mod.rs           # Wallet configuration (requires external signing)
│   ├── miner/
│   │   ├── mod.rs           # Mining module exports
│   │   └── engine.rs        # Multi-threaded AshMaize mining engine
│   └── coordinator/
│       └── mod.rs           # Mining coordinator (orchestration)
├── Cargo.toml               # Rust dependencies and build config
├── README.md                # Comprehensive documentation
├── TROUBLESHOOTING.md       # Troubleshooting guide
├── ARCHITECTURE.md          # This file
├── config.example.toml      # Example configuration
├── wallet.example.json      # Example wallet configuration
├── build.ps1                # Build script
└── test.ps1                 # Test script
```

## Architecture Principles

### 1. Separation of Concerns

Each module has a single, well-defined responsibility:

- **API Module**: Handles all HTTP communication with the Scavenger Mine service
- **Wallet Module**: Manages wallet configuration and signing (external signing)
- **Miner Module**: Implements the core mining algorithm with AshMaize
- **Coordinator Module**: Orchestrates the mining process (timing, submission, stats)
- **Config Module**: Manages application configuration

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

## Security Considerations

### Private Key Management

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

### System Requirements

- **OS**: Windows, Linux, macOS
- **RAM**: 2+ GB free (for ROM)
- **CPU**: Any modern processor (more cores = better)
- **Disk**: ~50 MB for binary and logs
- **Network**: Stable internet connection

### Runtime Behavior

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

Based on CPU architecture:

| CPU Type | Cores | Expected Rate |
|----------|-------|---------------|
| Mobile i5 | 4 | 50-150 H/s |
| Desktop i7 | 8 | 200-400 H/s |
| Ryzen 5950X | 16 | 500-1000 H/s |
| Threadripper | 32+ | 1000+ H/s |

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

## Acknowledgments

- **AshMaize**: ASIC-resistant hash algorithm by Input Output
- **Midnight Network**: NIGHT token and Scavenger Mine program
- **Rust Community**: Excellent tooling and libraries
