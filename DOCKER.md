# Docker Setup for NIGHT Token Miner

This guide covers running the NIGHT Token Miner in Docker, which is ideal for TrueNAS SCALE, home servers, or containerized environments.

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/SL13PNIR/night-scavenger-miner.git
cd night-scavenger-miner

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the miner
docker-compose down
```

### Option 2: Docker CLI

```bash
# Build the image
docker build -t night-miner .

# Run the container
docker run -d \
  --name night-miner \
  --restart unless-stopped \
  -v $(pwd)/auto-mine-wallet:/app/auto-mine-wallet \
  night-miner auto-mine --threads 2

# View logs
docker logs -f night-miner

# Stop the miner
docker stop night-miner
docker rm night-miner
```

## Configuration

### Adjusting Thread Count

Edit `docker-compose.yml` and change the `--threads` value:

```yaml
command: ["auto-mine", "--threads", "4"]  # Use 4 threads instead of 2
```

Or with Docker CLI:
```bash
docker run -d \
  --name night-miner \
  -v $(pwd)/auto-mine-wallet:/app/auto-mine-wallet \
  night-miner auto-mine --threads 4
```

### Resource Limits

To prevent the miner from consuming all system resources, uncomment the limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Maximum 2 CPU cores
      memory: 2G       # Maximum 2GB RAM
```

### Persistent Wallet Storage

The `auto-mine-wallet/` directory is mounted as a volume, so your addresses and progress persist across container restarts.

**Important:** Backup this directory regularly!

```bash
# Backup wallet
tar -czf wallet-backup-$(date +%Y%m%d).tar.gz auto-mine-wallet/

# Restore wallet
tar -xzf wallet-backup-YYYYMMDD.tar.gz
```

## TrueNAS SCALE Setup

### Method 1: Using TrueNAS Apps (GUI)

1. Go to **Apps** → **Discover Apps** → **Custom App**
2. **Application Name:** `night-miner`
3. **Image Repository:** Build locally first, or use Docker Compose from Shell
4. **Container Configuration:**
   - Command: `auto-mine`
   - Args: `--threads 2`
5. **Storage:**
   - Add Host Path: `/mnt/your-pool/night-miner-wallet` → `/app/auto-mine-wallet`
6. **Resources:**
   - CPU Limit: 2 cores
   - Memory Limit: 2GB

### Method 2: Using Shell (Recommended)

```bash
# SSH into TrueNAS SCALE
ssh admin@your-truenas-ip

# Navigate to a dataset (not system directory)
cd /mnt/your-pool/apps

# Clone repository
git clone https://github.com/SL13PNIR/night-scavenger-miner.git
cd night-scavenger-miner

# Edit docker-compose.yml to adjust threads if needed
nano docker-compose.yml

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Monitoring

### View Real-time Logs
```bash
docker-compose logs -f
# or
docker logs -f night-miner
```

### Check Container Status
```bash
docker-compose ps
# or
docker ps
```

### Check Resource Usage
```bash
docker stats night-miner
```

## Updating the Miner

```bash
# Stop container
docker-compose down

# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# Verify it's running
docker-compose logs -f
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs

# Check if port conflicts exist
docker ps -a
```

### High CPU Usage
Reduce thread count in `docker-compose.yml`:
```yaml
command: ["auto-mine", "--threads", "1"]
```

### Wallet Not Persisting
Ensure the volume mount is correct:
```bash
docker inspect night-miner | grep -A 5 Mounts
```

### Container Keeps Restarting
```bash
# View exit reason
docker-compose logs --tail 50

# Run interactively to debug
docker run -it --rm \
  -v $(pwd)/auto-mine-wallet:/app/auto-mine-wallet \
  night-miner auto-mine --threads 2
```

## Advanced Configuration

### Running Multiple Miners (Not Recommended)

If you want to run on multiple machines but share the wallet:

**DO NOT run multiple instances simultaneously with the same wallet!** This will cause conflicts in the `challenge_submissions` tracking.

Instead:
1. Run one instance at a time
2. Or use separate wallet directories for each machine
3. Consolidate rewards later (when donate_to API is fixed)

### Custom Network Configuration

```yaml
services:
  night-miner:
    network_mode: host  # Use host network instead of bridge
```

### Adding Health Checks

```yaml
services:
  night-miner:
    healthcheck:
      test: ["CMD", "ps", "aux", "|", "grep", "night-miner"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Performance Expectations

### TrueNAS DXP4800 Plus (Pentium Gold G6405)
- **Threads:** 2-4 (out of 4 available)
- **Expected Hash Rate:** 500-1,500 H/s
- **Solutions:** ~1-2 per hour
- **Impact:** Moderate CPU usage, minimal impact on file services

### Comparison
- Browser miner: ~52 H/s
- Docker on DXP4800: ~1,000 H/s (20× faster)
- Native on laptop (i9-11900H): ~9,500 H/s (180× faster than browser)

## Security Notes

1. **Wallet Security:** The `auto-mine-wallet/` directory contains private keys
   - Set proper permissions: `chmod 700 auto-mine-wallet/`
   - Backup regularly to secure location
   - Don't expose to network shares unnecessarily

2. **Container Security:**
   - Don't run as privileged unless necessary
   - Keep Docker updated
   - Review logs for suspicious activity

## Resource Recommendations

### For TrueNAS SCALE (DXP4800 Plus)
- **Threads:** 2 (leaves 2 for system)
- **CPU Limit:** 2 cores
- **Memory Limit:** 2GB
- **Impact:** Low to moderate

### For Dedicated Mining Server
- **Threads:** All available threads
- **No CPU limits**
- **Memory:** 2GB minimum
- **Impact:** 100% CPU usage (expected)

## Support

For issues specific to Docker deployment, check:
1. Docker logs: `docker-compose logs`
2. Container status: `docker ps -a`
3. System resources: `docker stats`
4. TrueNAS system logs: System Settings → Shell → `dmesg`

For miner-specific issues, see the main [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide.
