# Docker Security Options

This directory contains multiple Dockerfile options with different security profiles. **We recommend using the root-less versions for production deployments.**

## 🔒 **Recommended: Root-less Architectures**

### `Dockerfile.rootless` (Recommended)
- ✅ **Full-featured with supervisord process management**
- ✅ **Runs as vortex user (UID 1000) throughout entire lifecycle** 
- ✅ **No root privileges during execution**
- ✅ **Built-in scheduling with supervisord**
- ✅ **Comprehensive process monitoring**
- ✅ **Uses uv for fast dependency installation**

**Use case**: Production deployments requiring robust scheduling and process management

### `Dockerfile.simple.rootless` (Recommended for simple use cases)
- ✅ **Minimal complexity with security best practices**
- ✅ **Runs as vortex user (UID 1000) throughout entire lifecycle**
- ✅ **No root privileges during execution**
- ✅ **Uses traditional pip (no uv dependency)**
- ✅ **Simple health monitoring loop**
- ⚠️ **No built-in scheduling** (relies on external schedulers)

**Use case**: Simple deployments, one-time runs, or when using external scheduling

## ⚠️ **Legacy: Root-privileged Architectures**

### `Dockerfile` (Legacy - Security Issues)
- ❌ **Runs as root for cron daemon setup**
- ❌ **Complex root/non-root user switching**
- ❌ **Privilege escalation vulnerabilities**
- ❌ **Configuration path inconsistencies**
- ✅ Uses uv for fast dependency installation
- ✅ Full cron scheduling support

**Status**: Legacy - maintained for backward compatibility only

### `Dockerfile.simple` (Legacy - Security Issues)  
- ❌ **Runs as root for cron daemon setup**
- ❌ **Complex root/non-root user switching** 
- ❌ **Privilege escalation vulnerabilities**
- ❌ **Configuration path inconsistencies**
- ✅ Uses traditional pip (no uv dependency)
- ✅ Full cron scheduling support

**Status**: Legacy - maintained for backward compatibility only

## 🚀 **Migration Guide**

### From `Dockerfile` → `Dockerfile.rootless`
```bash
# Old (insecure)
docker build -f docker/Dockerfile -t vortex:latest .
docker-compose -f docker/docker-compose.yml up -d

# New (secure) 
docker build -f docker/Dockerfile.rootless -t vortex:latest .
docker-compose -f docker/docker-compose-rootless.yml up -d
```

### From `Dockerfile.simple` → `Dockerfile.simple.rootless`
```bash
# Old (insecure)
docker build -f docker/Dockerfile.simple -t vortex:latest .

# New (secure)
docker build -f docker/Dockerfile.simple.rootless -t vortex:latest .
```

### Volume Mount Changes
```yaml
# Old (root paths)
volumes:
  - ./config:/root/.config/vortex

# New (user paths)  
volumes:
  - ./config:/home/vortex/.config/vortex
```

## 🛡️ **Security Benefits of Root-less Architecture**

1. **No Privilege Escalation**: Container never has root privileges during execution
2. **Consistent User Context**: All operations run as UID 1000 (vortex user)
3. **Simplified Permissions**: Volume mounts have predictable ownership
4. **Reduced Attack Surface**: No system cron daemon or root access
5. **Better Isolation**: Process-level isolation from host system
6. **Compliance**: Meets container security best practices

## 📋 **Comparison Matrix**

| Feature | `Dockerfile.rootless` | `Dockerfile.simple.rootless` | `Dockerfile` (Legacy) | `Dockerfile.simple` (Legacy) |
|---------|:---------------------:|:----------------------------:|:---------------------:|:----------------------------:|
| **Security** | ✅ Root-less | ✅ Root-less | ❌ Root-privileged | ❌ Root-privileged |
| **Process Management** | ✅ Supervisord | ⚠️ Basic | ✅ System Cron | ✅ System Cron |
| **Build Speed** | ✅ Fast (uv) | ⚠️ Slower (pip) | ✅ Fast (uv) | ⚠️ Slower (pip) |
| **Complexity** | ⚠️ Moderate | ✅ Simple | ❌ Complex | ⚠️ Moderate |
| **Production Ready** | ✅ Yes | ✅ Yes | ❌ Security Issues | ❌ Security Issues |

## 🎯 **Recommendations**

- **Production**: Use `Dockerfile.rootless` + `docker-compose-rootless.yml`
- **Development**: Use `Dockerfile.simple.rootless` for quick testing
- **CI/CD**: Use `Dockerfile.simple.rootless` for one-time data downloads
- **Legacy Systems**: Only use root-privileged versions if absolutely necessary

Remember: **Security should be the default, not an afterthought!**