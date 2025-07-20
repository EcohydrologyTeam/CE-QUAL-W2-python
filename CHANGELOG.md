# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-20

### Added
- Modern Python package structure with `pyproject.toml`
- Organized code into logical subpackages:
  - `cequalw2.io` for data reading/writing
  - `cequalw2.visualization` for plotting functionality
  - `cequalw2.analysis` for reports and statistics
  - `cequalw2.utils` for utility functions
- Separated applications from library code
- Comprehensive test suite with pytest
- Development tools: black, isort, flake8, mypy, pre-commit
- Type hints and documentation improvements
- Console scripts for easy application launching

### Changed
- **BREAKING**: Reorganized package structure
- **BREAKING**: Updated import paths for all modules
- Applications moved to separate `apps/` directory
- Test data and examples better organized
- Updated development environment setup

### Migration Guide
- Old: `from cequalw2.w2_io import read_file`
- New: `from cequalw2.io import read_file`
- Old: `from cequalw2.w2_visualization import plot_time_series`
- New: `from cequalw2.visualization import plot_time_series`
- Applications now launched via console scripts or from `apps/` directory