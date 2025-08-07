# Docker Security Architecture

This directory contains secure Docker configurations that follow container security best practices. **All Docker files now use root-less architecture by default.**

## 🔒 **Secure Container Options**

### `Dockerfile` (Production Recommended)
- ✅ **Full-featured with supervisord process management**
- ✅ **Runs as vortex user (UID 1000) throughout entire lifecycle** 
- ✅ **No root privileges during execution**
- ✅ **Built-in scheduling with supervisord**
- ✅ **Comprehensive process monitoring**
- ✅ **Uses uv for fast dependency installation**
- ✅ **Multi-stage build for optimized image size**

**Use case**: Production deployments requiring robust scheduling and process management

### `Dockerfile.simple` (Simple Deployments)
- ✅ **Minimal complexity with security best practices**
- ✅ **Runs as vortex user (UID 1000) throughout entire lifecycle**
- ✅ **No root privileges during execution**
- ✅ **Uses traditional pip (no uv dependency)**
- ✅ **Simple health monitoring loop**
- ⚠️ **No built-in scheduling** (relies on external schedulers)
- ✅ **Single-stage build for simplicity**

**Use case**: Simple deployments, one-time runs, or when using external scheduling

## 🚀 **Quick Start**

### Production Deployment
```bash
# Full-featured container with supervisord scheduling
docker build -f docker/Dockerfile -t vortex:latest .
docker-compose -f docker/docker-compose.yml up -d
```

### Simple Deployment
```bash
# Minimal container for one-time runs or external scheduling
docker build -f docker/Dockerfile.simple -t vortex:simple .
docker run --rm -v $(pwd)/data:/data vortex:simple
```

### Configuration
All containers now use secure user paths by default:
```yaml
volumes:
  - ./config:/home/vortex/.config/vortex  # User configuration
  - ./data:/data                          # Output data
```

## 🛡️ **Security Benefits of Root-less Architecture**

1. **No Privilege Escalation**: Container never has root privileges during execution
2. **Consistent User Context**: All operations run as UID 1000 (vortex user)
3. **Simplified Permissions**: Volume mounts have predictable ownership
4. **Reduced Attack Surface**: No system cron daemon or root access
5. **Better Isolation**: Process-level isolation from host system
6. **Compliance**: Meets container security best practices

## 📋 **Comparison Matrix**

| Feature | `Dockerfile` | `Dockerfile.simple` |
|---------|:------------:|:-------------------:|
| **Security** | ✅ Root-less | ✅ Root-less |
| **Process Management** | ✅ Supervisord | ⚠️ Basic Loop |
| **Build Speed** | ✅ Fast (uv) | ⚠️ Slower (pip) |
| **Build Complexity** | ⚠️ Multi-stage | ✅ Single-stage |
| **Runtime Complexity** | ⚠️ Moderate | ✅ Simple |
| **Scheduling** | ✅ Built-in | ⚠️ External |
| **Production Ready** | ✅ Yes | ✅ Yes |

## 🎯 **Recommendations**

- **Production**: Use `Dockerfile` + `docker-compose.yml` for full-featured deployments
- **Development**: Use `Dockerfile.simple` for quick testing and prototyping  
- **CI/CD**: Use `Dockerfile.simple` for one-time data downloads
- **Container Orchestration**: Both options work well with Kubernetes, Docker Swarm, etc.

**All options are secure by default - choose based on your feature requirements!**