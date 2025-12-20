# Docker Guide for flac-detective

This guide covers how to use flac-detective with Docker for easy deployment and consistent environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Available Images](#available-images)
- [Basic Usage](#basic-usage)
- [Docker Compose](#docker-compose)
- [Building Locally](#building-locally)
- [Advanced Usage](#advanced-usage)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Pull and Run from GitHub Container Registry

```bash
# Pull the latest image
docker pull ghcr.io/guillainm/flac-detective:latest

# Analyze a FLAC file
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data/file.flac

# Repair a FLAC file
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data/file.flac --repair
```

## Available Images

Images are published to GitHub Container Registry (ghcr.io):

- `ghcr.io/guillainm/flac-detective:latest` - Latest stable version from main branch
- `ghcr.io/guillainm/flac-detective:v0.8.0` - Specific version tag
- `ghcr.io/guillainm/flac-detective:0.8` - Major.minor version
- `ghcr.io/guillainm/flac-detective:main` - Latest commit on main branch

All images are multi-architecture (amd64 and arm64).

## Basic Usage

### Analyze a Single File

```bash
docker run --rm \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data/your-file.flac
```

### Analyze a Directory

```bash
docker run --rm \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data --recursive
```

### Repair Files with Output

```bash
docker run --rm \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac --repair --output /data/output_dir
```

### Generate JSON Report

```bash
docker run --rm \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data --recursive --report /data/report.json
```

### Batch Processing

```bash
docker run --rm \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data --recursive --batch --repair --output /data/repaired
```

## Docker Compose

### Basic Setup

Create a `docker-compose.yml` file:

```yaml
version: '3.9'

services:
  flac-detective:
    image: ghcr.io/guillainm/flac-detective:latest
    volumes:
      - ./audio_files:/data:rw
    command: ["/data", "--recursive"]
```

Run with:

```bash
docker-compose run --rm flac-detective
```

### Custom Commands

```bash
# Analyze with custom options
docker-compose run --rm flac-detective /data/file.flac --verbose

# Repair files
docker-compose run --rm flac-detective /data --recursive --repair --batch
```

## Building Locally

### Build from Source

```bash
# Clone the repository
git clone https://github.com/guillainm/flac-detective.git
cd flac-detective

# Build the image
docker build -t flac-detective:local .

# Run your local build
docker run --rm -v /path/to/audio:/data flac-detective:local /data/file.flac
```

### Build with Docker Compose

```bash
docker-compose build
docker-compose run --rm flac-detective /data/file.flac
```

### Multi-Architecture Build

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t flac-detective:multi-arch \
  --push .
```

## Advanced Usage

### Interactive Shell

```bash
# Run bash inside the container
docker run --rm -it \
  -v /path/to/audio:/data \
  --entrypoint /bin/bash \
  ghcr.io/guillainm/flac-detective:latest

# Inside container, run commands
flac-detective /data/file.flac
```

### Custom User/Group

```bash
# Run as specific user to match file permissions
docker run --rm \
  -v /path/to/audio:/data \
  --user $(id -u):$(id -g) \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac
```

### Resource Limits

```bash
# Limit CPU and memory
docker run --rm \
  -v /path/to/audio:/data \
  --cpus="2.0" \
  --memory="2g" \
  ghcr.io/guillainm/flac-detective:latest \
  /data --recursive
```

### Environment Variables

```bash
docker run --rm \
  -v /path/to/audio:/data \
  -e PYTHONUNBUFFERED=1 \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac
```

### Network Isolation

```bash
# Run without network access (air-gapped)
docker run --rm \
  --network none \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac
```

## Security

### Security Features

The Docker image includes several security best practices:

- **Non-root user**: Runs as user `flacuser` (UID 1000)
- **Read-only root filesystem**: Prevents container modifications
- **No new privileges**: Prevents privilege escalation
- **Minimal base**: Based on python:3.11-slim
- **Regular scanning**: Images scanned with Trivy for vulnerabilities
- **SBOM generation**: Software Bill of Materials included

### Verify Image Signature

```bash
# Pull specific version
docker pull ghcr.io/guillainm/flac-detective:v0.8.0

# Inspect image
docker inspect ghcr.io/guillainm/flac-detective:v0.8.0

# Check labels
docker inspect ghcr.io/guillainm/flac-detective:v0.8.0 | grep -A 10 Labels
```

### Run with Additional Security

```bash
docker run --rm \
  -v /path/to/audio:/data:ro \
  --read-only \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac
```

## Troubleshooting

### Permission Issues

If you encounter permission errors:

```bash
# Option 1: Run as your user
docker run --rm --user $(id -u):$(id -g) -v /path/to/audio:/data ...

# Option 2: Fix permissions after run
sudo chown -R $USER:$USER /path/to/audio
```

### Volume Mounting on Windows

```bash
# Windows PowerShell
docker run --rm -v ${PWD}/audio_files:/data ghcr.io/guillainm/flac-detective:latest /data

# Windows CMD
docker run --rm -v %CD%/audio_files:/data ghcr.io/guillainm/flac-detective:latest /data
```

### Check Container Logs

```bash
# Run with verbose output
docker run --rm -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac --verbose

# Keep container for debugging
docker run -it --name flac-debug \
  -v /path/to/audio:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data/file.flac

# View logs
docker logs flac-debug
```

### Verify Installation

```bash
# Check version
docker run --rm ghcr.io/guillainm/flac-detective:latest --version

# Check help
docker run --rm ghcr.io/guillainm/flac-detective:latest --help

# Test with example file
docker run --rm -v /path/to/test.flac:/data/test.flac \
  ghcr.io/guillainm/flac-detective:latest /data/test.flac
```

### Image Size Issues

```bash
# Check image size
docker images ghcr.io/guillainm/flac-detective

# Clean up old images
docker image prune -a

# Pull specific version
docker pull ghcr.io/guillainm/flac-detective:v0.8.0
```

## Best Practices

1. **Pin versions**: Use specific version tags in production
2. **Mount read-only**: Use `:ro` for input directories when only analyzing
3. **Use volumes**: For better performance with large audio libraries
4. **Resource limits**: Set appropriate CPU/memory limits
5. **Health checks**: Add health checks in docker-compose
6. **Logging**: Use `-e PYTHONUNBUFFERED=1` for real-time logs

## Examples

### Production Analysis Pipeline

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  analyzer:
    image: ghcr.io/guillainm/flac-detective:v0.8.0
    volumes:
      - /mnt/audio:/data:ro
      - /mnt/reports:/reports:rw
    command: ["/data", "--recursive", "--report", "/reports/analysis.json"]
    restart: on-failure
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
```

### Automated Repair Service

```yaml
# docker-compose.repair.yml
version: '3.9'

services:
  repairer:
    image: ghcr.io/guillainm/flac-detective:latest
    volumes:
      - /mnt/incoming:/input:ro
      - /mnt/repaired:/output:rw
    command: ["/input", "--recursive", "--repair", "--batch", "--output", "/output"]
    environment:
      - PYTHONUNBUFFERED=1
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/guillainm/flac-detective/issues
- Documentation: https://flac-detective.readthedocs.io
