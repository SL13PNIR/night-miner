# NIGHT Miner - Bug Fix Summary

## Problem
All mining solutions were rejected by the server with "Solution does not meet difficulty" error, despite passing local validation checks.

## Root Cause
**ROM Initialization Bug** - The mining engine was initializing the AshMaize ROM (1GB lookup table) with **decoded hex bytes** instead of **hex string bytes**.

### The Bug
```rust
// WRONG - Decoded the hex string into binary bytes
let seed = hex::decode(no_pre_mine).context("Failed to decode no_pre_mine hex")?;
```

### The Fix
```rust
// CORRECT - Use the hex string bytes directly
let seed = no_pre_mine.as_bytes();
```

## Why This Mattered
The ROM (Read-Only Memory) is a 1GB deterministically-generated lookup table that is fundamental to the AshMaize hash algorithm. The ROM must be initialized with the exact same seed as the website uses.

The website does:
```javascript
builder.key(new TextEncoder().encode(no_pre_mine))
```

This encodes the **hex string itself** (e.g., "e8a195800bae5751...") as UTF-8 bytes, NOT the decoded binary representation.

Using different keys created completely different ROMs, which produced completely different hashes, causing all our locally-valid solutions to be rejected by the server.

## Additional Fix
Updated API endpoint from old URL to current production endpoint:
- Old: `https://scavenger.prod.gd.midnighttge.io`
- New: `https://sm.midnight.gd/api`

## Verification
Created test program that verified AshMaize implementation against official test vector:
- Input: key="123", salt="hello", 8 loops, 256 instructions
- Expected hash matched perfectly ✅

## Result
After fix was applied:
- First solution submitted: **ACCEPTED** ✅
- Success rate: 100%
- Miner now working correctly

## Files Changed
1. `src/miner/engine.rs` - ROM initialization fix (line 65)
2. `src/api/client.rs` - API endpoint update (line 7)

## Lessons Learned
When debugging hash mismatches:
1. Verify the hash algorithm implementation is correct (test vectors)
2. Verify input data formatting matches exactly (preimage construction)
3. **Verify initialization parameters match exactly** (ROM seed encoding)

The bug was subtle because:
- Both approaches seemed reasonable
- The code compiled and ran without errors
- Local validation passed (difficulty check logic was correct)
- Only server-side validation revealed the mismatch
