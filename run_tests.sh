#!/bin/bash
# DockAI Test Runner Script

set -e

echo "🧪 DockAI Test Suite"
echo "===================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
else
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        source .venv/bin/activate
    fi
    echo "✅ Virtual environment activated"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q -e .
pip install -q -r requirements-test.txt
echo "✅ Dependencies installed"

# Run tests
echo ""
echo "🏃 Running tests..."
echo ""

if [ "$1" == "--coverage" ]; then
    pytest --cov=src/dockai --cov-report=html --cov-report=term-missing
    echo ""
    echo "📊 Coverage report generated in htmlcov/index.html"
elif [ "$1" == "--verbose" ]; then
    pytest -vv
elif [ "$1" == "--fast" ]; then
    pytest -x  # Stop on first failure
elif [ -n "$1" ]; then
    # Run specific test file or test
    pytest "$1" -v
else
    pytest
fi

echo ""
echo "✅ Tests complete!"
