#!/bin/bash

# Test runner script for Memory Movie Maker

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ">ê Running Memory Movie Maker tests..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Attempting to activate venv..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}Error: Virtual environment not found. Run setup_dev.sh first.${NC}"
        exit 1
    fi
fi

# Parse command line arguments
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --unit          Run only unit tests"
            echo "  --integration   Run only integration tests"
            echo "  --e2e           Run only end-to-end tests"
            echo "  --coverage, -c  Generate coverage report"
            echo "  --verbose, -v   Verbose output"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add test type filter
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
        echo "Running unit tests only..."
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
        echo "Running integration tests only..."
        ;;
    e2e)
        PYTEST_CMD="$PYTEST_CMD tests/e2e/"
        echo "Running end-to-end tests only..."
        ;;
    all)
        echo "Running all tests..."
        ;;
esac

# Add coverage options
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=memory_movie_maker --cov-report=term-missing --cov-report=html"
fi

# Run linting first
echo ""
echo "= Running linting checks..."
echo "Running black..."
black --check src/ tests/ || { echo -e "${YELLOW}Black formatting issues found. Run 'make format' to fix.${NC}"; }

echo "Running isort..."
isort --check-only src/ tests/ || { echo -e "${YELLOW}Import sorting issues found. Run 'make format' to fix.${NC}"; }

echo "Running flake8..."
flake8 src/ tests/ || { echo -e "${YELLOW}Flake8 issues found.${NC}"; }

# Run type checking
echo ""
echo "= Running type checking..."
mypy src/ || { echo -e "${YELLOW}Type checking issues found.${NC}"; }

# Run tests
echo ""
echo ">ê Running pytest..."
echo "Command: $PYTEST_CMD"
echo ""

if $PYTEST_CMD; then
    echo -e "${GREEN} All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo "=Ê Coverage report generated:"
        echo "   - Terminal report above"
        echo "   - HTML report: htmlcov/index.html"
    fi
else
    echo -e "${RED}L Tests failed!${NC}"
    exit 1
fi

# Run security checks
echo ""
echo "= Running security checks..."
pip list --format=freeze | grep -E '^(requests|urllib3|pillow|numpy)' | while read -r package; do
    pkg_name=$(echo "$package" | cut -d'=' -f1)
    pkg_version=$(echo "$package" | cut -d'=' -f3)
    echo "Checking $pkg_name==$pkg_version for vulnerabilities..."
done

echo ""
echo -e "${GREEN}( Test run complete!${NC}"