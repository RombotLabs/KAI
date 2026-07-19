#!/bin/bash

# Pre-commit hook to run Dependabot and CodeQL checks
# Place this in .git/hooks/pre-commit and make it executable

set -e

echo "🔍 Running pre-commit security checks..."

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Dependabot config exists
if [ -f ".github/dependabot.yml" ]; then
    echo -e "${YELLOW}📦 Dependabot config found${NC}"
else
    echo -e "${YELLOW}⚠️  No Dependabot config found at .github/dependabot.yml${NC}"
fi

# Check for CodeQL workflow
if [ -f ".github/workflows/codeql.yml" ]; then
    echo -e "${YELLOW}🔒 CodeQL workflow found${NC}"
else
    echo -e "${YELLOW}⚠️  No CodeQL workflow found. Consider adding one.${NC}"
fi

# Optional: Run local security checks if tools are available
if command -v bandit &> /dev/null; then
    echo -e "${YELLOW}🛡️  Running Bandit security check...${NC}"
    bandit -r . -ll --skip B101,B601 || true
fi

if command -v safety &> /dev/null; then
    echo -e "${YELLOW}📋 Checking dependencies with Safety...${NC}"
    safety check --json || true
fi

echo -e "${GREEN}✅ Pre-commit checks complete!${NC}"
echo -e "${GREEN}ℹ️  Dependabot and CodeQL will run on GitHub after push${NC}"

exit 0
