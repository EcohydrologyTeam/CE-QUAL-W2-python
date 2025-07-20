# CE-QUAL-W2-python

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive Python toolkit for CE-QUAL-W2 hydrodynamic and water quality model data analysis and visualization.

## Features

- **Data I/O**: Read CE-QUAL-W2 formats (.npt, .opt, .csv) and export to modern formats (SQLite, HDF5, NetCDF)
- **Visualization**: Interactive plotting with Holoviews/Bokeh and traditional matplotlib support
- **Analysis**: Statistical analysis and automated report generation
- **Applications**: Desktop (PyQt5) and web-based (Panel) data viewers
- **Modern Python**: Type hints, comprehensive testing, automated code quality

## Installation

### Development Installation

```bash
# Clone the repository
git clone https://github.com/EcohydrologyTeam/CE-QUAL-W2-python.git
cd CE-QUAL-W2-python

# Create conda environment
conda env create -f environment.yml
conda activate cequalw2

# Install in development mode
pip install -e .
```

### Production Installation

```bash
pip install cequalw2
```

## Quick Start

### Library Usage

```python
import cequalw2 as w2

# Read CE-QUAL-W2 data files
df = w2.read_file("2006_Met.npt")

# Create visualizations
w2.plot_time_series(df, "Temperature")

# Export to modern formats
w2.write_to_sqlite(df, "output.db")
```

### Applications

Launch the desktop GUI:
```bash
clearview
```

Launch the web application:
```bash
clearview-web
```

## Supported Data Formats

### Input Formats
- **`.npt` files**: Fixed-width CE-QUAL-W2 time series
- **`.opt` files**: Fixed-width optimization/output data  
- **`.csv` files**: Comma-separated versions of the above

### Output Formats
- **SQLite (`.db`)**: Lightweight database storage
- **HDF5 (`.h5`)**: High-performance scientific data
- **NetCDF (`.nc`)**: Standards-compliant scientific data

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run code quality checks
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### Project Structure

```
CE-QUAL-W2-python/
├── src/cequalw2/           # Main library
│   ├── io/                 # Data I/O functionality
│   ├── visualization/      # Plotting and visualization
│   ├── analysis/          # Statistics and reports
│   └── utils/             # Utility functions
├── apps/clearview/        # Applications
│   ├── gui/               # PyQt5 desktop app
│   ├── web/               # Panel web app
│   └── assets/            # Static files
├── tests/                 # Test suite
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and code quality checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

- **Todd E. Steissberg, PhD, PE** - *Lead Developer* - Ecohydrology Team, ERDC, U.S. Army Corps of Engineers

## Acknowledgments

- U.S. Army Corps of Engineers Engineer Research and Development Center (ERDC)
- Water Quality and Contaminant Modeling Branch
- Ecohydrology Team
