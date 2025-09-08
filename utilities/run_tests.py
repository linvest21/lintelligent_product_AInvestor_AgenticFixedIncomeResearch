#!/usr/bin/env python3
"""
LINVEST21 Test Runner
Quick script to run tests with proper Python path setup
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import pytest
    
    # Default to rating engine tests if no arguments
    if len(sys.argv) == 1:
        sys.argv.append("tests/test_rating_engine.py")
    
    # Run pytest with arguments
    exit_code = pytest.main(sys.argv[1:])
    sys.exit(exit_code)