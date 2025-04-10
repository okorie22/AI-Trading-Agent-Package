# AI Trading System Desktop Application - Installation Guide

This document provides instructions for installing and running the AI Trading System desktop application with its cyberpunk-themed UI.

## Prerequisites

Before installing the application, ensure you have the following:

1. Python 3.8 or higher installed
2. Pip package manager
3. Git (optional, for cloning the repository)

## Required Python Packages

The application requires the following Python packages:

```
PySide6>=6.4.0
PyInstaller>=5.6.0
Pillow>=9.0.0  # For icon generation
matplotlib>=3.5.0  # For font management
```

You can install these packages using pip:

```bash
pip install PySide6 PyInstaller Pillow matplotlib
```

## Installation Options

### Option 1: Run from Source

1. Clone or download the repository
2. Navigate to the repository directory
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python trading_ui_connected.py
   ```

### Option 2: Build Executable

1. Clone or download the repository
2. Navigate to the repository directory
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the build script:
   ```bash
   python build.py
   ```
5. The executable will be created in the `dist/AI_Trading_System` directory
6. You can also find a zip file of the distribution in the current directory

## Running the Application

### From Source
```bash
python trading_ui_connected.py
```

### From Executable
- **Windows**: Double-click `AI_Trading_System.exe` in the `dist\AI_Trading_System` directory
- **macOS**: Double-click `AI_Trading_System` in the `dist/AI_Trading_System` directory
- **Linux**: Run `./AI_Trading_System` in the `dist/AI_Trading_System` directory

## Configuration

The application will automatically look for your trading system's configuration files:

1. `config.py` - Contains system-wide configuration settings
2. `.env` file - Contains environment variables like API keys and wallet addresses

If these files are not found in the current directory, the application will use default values.

## Command Line Arguments

The application supports the following command line arguments:

- `--config PATH` - Specify the path to your config.py file
- `--src PATH` - Specify the path to your src directory containing agent code

Example:
```bash
python trading_ui_connected.py --config /path/to/config.py --src /path/to/src
```

Or with the executable:
```bash
./AI_Trading_System --config /path/to/config.py --src /path/to/src
```

## Troubleshooting

If you encounter any issues:

1. Ensure all dependencies are installed correctly
2. Check that your config.py file is properly formatted
3. Verify that your agent code files exist in the expected locations
4. For executable issues, try running from source to see more detailed error messages

## Contact

If you need further assistance, please contact the developer.
