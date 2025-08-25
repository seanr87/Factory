#!/bin/bash
# Test Factory workflows locally
# Requires: act (https://github.com/nektos/act)

set -e

echo "🧪 Testing Factory Workflows"
echo "============================"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ 'act' is not installed"
    echo "Install from: https://github.com/nektos/act"
    exit 1
fi

# Test provision-study workflow
echo ""
echo "📋 Testing provision-study.yml..."
echo "----------------------------------"

act workflow_dispatch \
    -W .github/workflows/provision-study.yml \
    --input study_title="Test Study" \
    --input lead_name="John Doe" \
    --input lead_github="johndoe" \
    --input target_date="2025-12-31" \
    --dryrun

if [ $? -eq 0 ]; then
    echo "✅ provision-study.yml validation passed"
else
    echo "❌ provision-study.yml validation failed"
    exit 1
fi

# Test factory-sync workflow
echo ""
echo "📋 Testing factory-sync.yml..."
echo "-------------------------------"

act workflow_dispatch \
    -W .github/workflows/factory-sync.yml \
    --dryrun

if [ $? -eq 0 ]; then
    echo "✅ factory-sync.yml validation passed"
else
    echo "❌ factory-sync.yml validation failed"
    exit 1
fi

echo ""
echo "✨ All workflow tests passed!"
echo ""
echo "Note: This was a dry run. To test with actual execution:"
echo "  Remove --dryrun flag and set up secrets in .secrets file"