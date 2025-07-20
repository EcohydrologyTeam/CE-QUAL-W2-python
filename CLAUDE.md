# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CE-QUAL-W2-python is a modern, comprehensive toolkit for analyzing and visualizing CE-QUAL-W2 hydrodynamic and water quality model data. The project follows Python packaging best practices with a clean separation between library code and applications.

## Development Environment

### Installation
```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate cequalw2

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Key Dependencies
- Python 3.9+ (supports 3.9-3.12)
- Core: pandas, numpy, matplotlib, seaborn
- Visualization: holoviews, panel, bokeh
- GUI: PyQt5
- Storage: h5py, sqlalchemy
- Development: pytest, black, isort, flake8, mypy, pre-commit

## Modern Architecture

### Core Library (`src/cequalw2/`)
- **`io/`**: Data reading/writing (`readers.py` for .npt/.opt/.csv files)
- **`visualization/`**: Plotting engine (`plots.py` with matplotlib/holoviews)
- **`analysis/`**: Statistics and reports (`reports.py`, `statistics.py`)
- **`utils/`**: Utilities (`datetime.py` for CE-QUAL-W2 time conversion)
- **`apps/`**: Application entry points for console scripts

### Applications (`apps/clearview/`)
- **`gui/main.py`**: PyQt5 desktop application
- **`web/main.py`**: Panel/Holoviews web application
- **`assets/`**: Icons and static files

### Testing (`tests/`)
- Comprehensive pytest test suite
- Organized by module: `test_io/`, `test_visualization/`, `test_analysis/`
- Test fixtures and sample data support

## Common Development Tasks

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cequalw2

# Run specific test module
pytest tests/test_io/test_readers.py

# Run tests matching pattern
pytest -k "test_file_reading"
```

### Code Quality
```bash
# Format code
black src/ tests/ apps/

# Sort imports
isort src/ tests/ apps/

# Lint code
flake8 src/ tests/ apps/

# Type checking
mypy src/
```

### Build and Install
```bash
# Install in development mode
pip install -e .

# Install with specific extras
pip install -e ".[dev,docs,notebooks]"

# Build distribution
python -m build
```

## Data Formats

### Input Formats
- **`.npt` files**: Fixed-width CE-QUAL-W2 time series (meteorology, inflows, water quality)
- **`.opt` files**: Fixed-width optimization/output data
- **`.csv` files**: Comma-separated versions of the above

### Output Formats
- **SQLite (`.db`)**: Processed time series storage
- **HDF5 (`.h5`)**: High-performance scientific data
- **NetCDF (`.nc`)**: Standards-compliant scientific data

### Configuration
- **YAML files**: Plot control specifications (`test/tests001/plots_*.yaml`)
- Use YAML files to define automated plotting workflows

## Key Conventions

### Import Patterns (Updated)
```python
# New modular imports
from cequalw2.io import read_file, write_to_sqlite
from cequalw2.visualization import plot_time_series
from cequalw2.analysis import generate_report
from cequalw2.utils import datetime_to_day_of_year

# Or import everything (maintains backward compatibility)
import cequalw2 as w2
df = w2.read_file("data.npt")
```

### File Reading
- Use `get_header_row_number()` to detect header rows (TSR files use row 0, others use row 2)
- Files starting with 'tsr' have different header conventions
- All data reading goes through pandas DataFrames

### Plotting
- Standard color palettes available: `rainbow`, `everest`, `k2`
- Configure plots via YAML files rather than hardcoding
- Support both single plots and multi-subplot layouts
- Use holoviews for interactive web plots, matplotlib for static plots

### Testing
- Write tests for new functionality in appropriate `tests/test_*/` directory
- Use fixtures from `tests/conftest.py` for common test data
- Test data available in `test/data/BerlinMilton2006/`

## Running Applications

### Console Scripts (Recommended)
```bash
# Desktop GUI
clearview

# Web application  
clearview-web
```

### Direct Execution
```bash
# Desktop GUI
python apps/clearview/gui/main.py

# Web application
python apps/clearview/web/main.py
```

### Development Tips
- Applications automatically handle import paths for the cequalw2 library
- Example notebooks available in `docs/examples/`
- Utility scripts in `scripts/` directory
- Use YAML plot control files in `test/tests001/` as templates