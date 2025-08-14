#!/usr/bin/env python3
"""
Debug script to run Barchart E2E tests with proper logging configuration.
"""

import os
import sys
import logging
import subprocess

# Add src to Python path
sys.path.insert(0, '/home/rosantos/workspace/projects/vortex/main/src')

# Import and initialize Vortex logging
try:
    from vortex.utils.logging_utils import init_logging
    init_logging(level=logging.DEBUG)
    print("✅ Vortex logging initialized")
except ImportError as e:
    print(f"⚠️ Could not import Vortex logging: {e}")
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    print("✅ Basic logging configured")

# Configure additional loggers that might be used
loggers_to_configure = [
    'vortex',
    'vortex.infrastructure.providers.barchart',
    'vortex.cli',
    'vortex.services',
    'urllib3.connectionpool',  # HTTP requests
    'requests.packages.urllib3.connectionpool'  # Alternative requests logging
]

for logger_name in loggers_to_configure:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

# Set environment variables
os.environ['VORTEX_LOG_LEVEL'] = 'DEBUG'
os.environ['PYTHONPATH'] = '/home/rosantos/workspace/projects/vortex/main/src'

print("🔧 VORTEX_LOG_LEVEL:", os.environ.get('VORTEX_LOG_LEVEL'))
print("🔧 Barchart credentials:", "✅ SET" if os.environ.get('VORTEX_BARCHART_USERNAME') else "❌ MISSING")
print("🔧 Configured loggers:", ', '.join(loggers_to_configure))
print("=" * 80)

# Run the test
cmd = [
    sys.executable, '-m', 'pytest',
    'tests/e2e/test_barchart_e2e.py::TestBarchartEndToEnd::test_barchart_download_workflow',
    '-v', '-s', '--tb=long', '--capture=no'
]

subprocess.run(cmd)