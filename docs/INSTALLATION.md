# TITAN Installation Guide

## System Requirements

- **Python**: 3.14 or later
- **OS**: Windows 10+, Ubuntu 20.04+, macOS 12+
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 500MB free space
- **Network**: Internet access for broker connectivity

## Installation from Source

```bash
# Clone the repository
git clone https://github.com/your-org/titan-cli.git
cd titan-cli

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"
```

## Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
# Minimum required for paper trading:
# TITAN_BROKER_PROVIDER=paper

# For live trading:
# TITAN_BROKER_PROVIDER=yfinance
# TITAN_BROKER_API_KEY=your_api_key
# TITAN_BROKER_CLIENT_ID=your_client_id
```

## Verify Installation

```bash
# Check version
titan version

# Check detailed version info
titan version -v

# Run system diagnostics
titan doctor

# Check configuration
titan config show

# Check live trading status (validates config, broker, risk limits)
titan live status --verbose

# Pre-flight check (validates without starting)
titan live start --dry-run
```

## Running TITAN

### CLI Commands

TITAN provides three trading modes and supporting subsystems:

```bash
# Paper trading (simulated, no broker connection)
titan paper start --verbose     # Start paper trading session
titan paper status              # Check session status
titan paper report              # Generate session report
titan paper stop                # Stop session

# Live trading (real broker, full validation)
titan live start --verbose      # Start with pre-flight checks
titan live status               # Check trading status
titan live health               # System health check
titan live positions            # Open positions
titan live orders               # Order history
titan live exposure             # Capital and margin
titan live report               # Operational report
titan live stop                 # Graceful shutdown

# Runtime engine (direct, no validation pipeline)
titan runtime start --verbose   # Start runtime directly
titan runtime status            # Check runtime status
titan runtime stop              # Stop runtime

# Backtesting (historical data replay)
titan backtest run RELIANCE nse --csv data.csv
titan backtest status
titan backtest report
titan backtest list
```

### Virtual Environment

Always run TITAN inside a virtual environment:

```bash
# Create (if not already done during installation)
python -m venv .venv

# Activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.\.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate

# Verify
titan version
```

### PATH Troubleshooting

If `titan` command is not found:

```bash
# 1. Check if installed in current venv
pip show titan

# 2. Check PATH includes venv Scripts/bin
# Windows:
echo $env:PATH
# Linux/macOS:
echo $PATH

# 3. Run directly via Python
python -m titan version

# 4. Reinstall in development mode
pip install -e .

# 5. Check pyproject.toml entry point
# Should have: titan = "titan.cli:app"
```

### Legacy Entry Point

The following also work but `titan` is preferred:

```bash
python -m titan version
python -m titan doctor
```

## Docker Installation

```bash
cd docker
docker compose build
docker compose up -d
```

## Platform-Specific Notes

### Windows
- Requires PowerShell 5.1+ for scripts
- Windows Defender may flag Python processes
- Use `.ps1` scripts for service management

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.14 python3.14-venv
```

### macOS
```bash
brew install python@3.14
```

## Uninstall

```bash
pip uninstall titan-cli
rm -rf .venv
rm -rf titan_cli.egg-info
```

## Verification
After installation, use the TUI (F7) to verify configuration and deployment parameters.
