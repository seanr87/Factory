# Factory Makefile
# Provides common development and validation tasks

.PHONY: help bootstrap lint validate test act brief clean

# Default target
help:
	@echo "Factory Development Commands:"
	@echo "  make bootstrap  - Install development dependencies"
	@echo "  make lint       - Run linters (actionlint, yamllint)"
	@echo "  make validate   - Run security and policy checks"
	@echo "  make test       - Run test suite"
	@echo "  make act        - Test workflows locally with act"
	@echo "  make brief      - Package briefing packet"
	@echo "  make clean      - Clean generated files"

# Install development dependencies
bootstrap:
	@echo "🔧 Installing development dependencies..."
	@echo "Note: This requires manual installation of:"
	@echo "  - actionlint: https://github.com/rhysd/actionlint"
	@echo "  - yamllint: pip install yamllint"
	@echo "  - act: https://github.com/nektos/act"
	@echo "  - Python 3.8+: for scripts and app"
	@pip install --user yamllint

# Lint workflows
lint:
	@echo "🔍 Linting workflows..."
	@if command -v actionlint >/dev/null 2>&1; then \
		actionlint .github/workflows/*.yml .github/workflows/*.yaml; \
	else \
		echo "⚠️  actionlint not installed, skipping..."; \
	fi
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint .github/workflows/*.yml .github/workflows/*.yaml; \
	else \
		echo "⚠️  yamllint not installed, skipping..."; \
	fi

# Validate security and policies
validate: lint
	@echo "🛡️  Validating security policies..."
	@python3 tools/validate_workflows.py

# Run tests
test:
	@echo "🧪 Running tests..."
	@echo "Note: Tests will be added as components are developed"

# Test workflows locally with act
act:
	@echo "🎬 Testing workflows with act..."
	@if command -v act >/dev/null 2>&1; then \
		act --list; \
	else \
		echo "⚠️  act not installed. Install from: https://github.com/nektos/act"; \
	fi

# Package briefing packet
brief:
	@echo "📦 Creating briefing.zip..."
	@python3 tools/package_briefing.py

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	@rm -f briefing.zip
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete

# Development shortcuts
.PHONY: dev
dev: lint
	@echo "✅ Quick validation complete"

.PHONY: all
all: bootstrap lint validate test brief
	@echo "✨ All tasks complete!"