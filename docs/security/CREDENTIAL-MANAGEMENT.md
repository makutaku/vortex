# Secure Credential Management

This document describes Vortex's secure credential management system, which ensures credentials are never hardcoded or committed to version control.

## Overview

Vortex implements a secure credential system that loads credentials from multiple sources in order of precedence:

1. **Environment Variables** (highest precedence)
2. **Local Environment Files** (`.env.local`, `.env`)
3. **User Configuration Directory** (`~/.vortex/credentials.json`)

## Security Features

- 🔒 **No hardcoded credentials** in source code
- 🚫 **Credential files excluded** from version control
- 📁 **Multiple secure sources** with clear precedence
- 🧪 **Test-friendly** with mock credential support
- ⚠️ **Graceful degradation** when credentials unavailable

## Usage

### Environment Variables

```bash
# Set via command line
export VORTEX_BARCHART_USERNAME=your_username
export VORTEX_BARCHART_PASSWORD=your_password

# Or add to your shell profile (.bashrc, .zshrc, etc.)
echo 'export VORTEX_BARCHART_USERNAME=your_username' >> ~/.bashrc
echo 'export VORTEX_BARCHART_PASSWORD=your_password' >> ~/.bashrc
```

### Local Environment Files

```bash
# Copy the example file
cp .env.example .env.local

# Edit with your credentials (safe - excluded from git)
vim .env.local
```

Example `.env.local`:
```env
# Barchart.com credentials
VORTEX_BARCHART_USERNAME=your_username
VORTEX_BARCHART_PASSWORD=your_password

# Other configuration
VORTEX_LOG_LEVEL=INFO
VORTEX_OUTPUT_DIR=./data
```

### User Configuration Directory

```bash
# Create user config directory
mkdir -p ~/.vortex

# Create credentials file
cat > ~/.vortex/credentials.json << 'EOF'
{
  "providers": {
    "barchart": {
      "username": "your_username", 
      "password": "your_password"
    }
  }
}
EOF

# Secure the file (read/write for owner only)
chmod 600 ~/.vortex/credentials.json
```

## API Usage

### Python Code

```python
from vortex.core.security.credentials import get_secure_barchart_credentials

# Get credentials securely
credentials = get_secure_barchart_credentials()
if credentials:
    username = credentials['username']
    password = credentials['password']
    # Use credentials...
else:
    # Handle missing credentials gracefully
    print("No Barchart credentials available")
```

### Test Code

```python
from tests.fixtures.secure_credentials import TestCredentialManager, require_barchart_credentials

# For unit tests (use mock credentials)
manager = TestCredentialManager()
mock_manager = manager.mock_credential_manager_with_test_creds()

# For integration tests (require real credentials)
@require_barchart_credentials()
def test_real_barchart_download():
    # Test only runs if real credentials available
    pass
```

## Migration Guide

### Replacing Hardcoded Credentials

**Before (INSECURE):**
```python
# ❌ Never do this
username = "hardcoded@example.com"
password = "hardcoded_password"
provider = BarchartDataProvider(username, password)
```

**After (SECURE):**
```python
# ✅ Use secure credential system
from vortex.core.security.credentials import get_secure_barchart_credentials

credentials = get_secure_barchart_credentials()
if not credentials:
    raise ConfigurationError("Barchart credentials not configured")

provider = BarchartDataProvider(
    credentials['username'], 
    credentials['password']
)
```

### Updating Tests

**Before:**
```python
# ❌ Hardcoded test credentials
def test_provider():
    provider = BarchartDataProvider("test@example.com", "test123")
```

**After:**
```python
# ✅ Secure test credentials
from tests.fixtures.secure_credentials import TestCredentialManager

def test_provider():
    manager = TestCredentialManager()
    mock_manager = manager.mock_credential_manager_with_test_creds()
    creds = mock_manager.get_barchart_credentials()
    provider = BarchartDataProvider(creds['username'], creds['password'])
```

## Git Security

The following files are automatically excluded from version control:

```gitignore
# Security - Credential files
.env
.env.local
.env.production
.env.development
credentials.json
*credentials*
!.env.example
!*credentials*.example
```

## Best Practices

1. **Never commit credentials** - Use `.env.local` for local development
2. **Use environment variables** in production deployments
3. **Rotate credentials regularly** and update in secure locations
4. **Use least-privilege** credentials (read-only when possible)
5. **Monitor credential usage** and detect unauthorized access
6. **Document credential requirements** in deployment guides

## Troubleshooting

### Credentials Not Found

```bash
# Check environment variables
printenv | grep VORTEX_BARCHART

# Check local environment files
cat .env.local

# Check user configuration
cat ~/.vortex/credentials.json

# Test credential loading
python -c "
from vortex.core.security.credentials import get_secure_barchart_credentials
creds = get_secure_barchart_credentials()
print('Found credentials:' if creds else 'No credentials found')
"
```

### Precedence Issues

If credentials seem wrong, check the precedence:
1. Environment variables override everything
2. `.env.local` overrides `.env` 
3. User config is lowest precedence

### File Permissions

Ensure credential files have secure permissions:
```bash
chmod 600 .env.local
chmod 600 ~/.vortex/credentials.json
```

## Security Considerations

- **File Permissions**: Credential files should be readable only by owner (600)
- **Network Security**: Always use HTTPS/TLS for credential transmission
- **Logging**: Never log raw credentials, only masked values
- **Error Messages**: Don't expose credentials in error messages
- **Memory**: Clear credentials from memory when possible
- **Backups**: Exclude credential files from automatic backups