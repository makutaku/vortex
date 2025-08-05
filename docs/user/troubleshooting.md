# Troubleshooting Guide

Common issues and solutions for Vortex users.

## Docker Issues

See [DOCKER-TROUBLESHOOTING.md](../DOCKER-TROUBLESHOOTING.md) for Docker-specific issues.

## Common Problems

### Dependencies Not Found
If you see import errors or "requires dependencies" messages:
```bash
# Reinstall with all dependencies
uv pip install -e ".[dev,test,lint]"
```

### Permission Issues
For file permission errors:
```bash
# Ensure output directory is writable
chmod 755 ./data
```

## Getting Help

1. Check the logs for detailed error messages
2. Verify your configuration with `vortex config --show`
3. Test provider connectivity with `vortex providers --test [provider]`