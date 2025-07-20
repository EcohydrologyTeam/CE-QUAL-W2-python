"""Shared test configuration and fixtures."""

import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent.parent / "test" / "data" / "BerlinMilton2006"


@pytest.fixture
def sample_npt_file(test_data_dir):
    """Sample .npt file for testing."""
    return test_data_dir / "2006_Met.npt"


@pytest.fixture
def sample_csv_file(test_data_dir):
    """Sample .csv file for testing."""
    return test_data_dir / "tsr_1_seg37.csv"


@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame for testing."""
    return pd.DataFrame({
        'datetime': pd.date_range('2006-01-01', periods=10, freq='D'),
        'temperature': [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0],
        'flow': [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0]
    })