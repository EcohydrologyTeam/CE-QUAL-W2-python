"""Tests for CE-QUAL-W2 data readers."""

import pytest
import pandas as pd
from pathlib import Path

from cequalw2.io.readers import FileType, get_header_row_number, read_file


class TestFileType:
    """Test FileType enumeration."""
    
    def test_file_type_values(self):
        """Test FileType enum values."""
        assert FileType.UNKNOWN.value == 0
        assert FileType.FIXED_WIDTH.value == 1
        assert FileType.CSV.value == 2


class TestHeaderRowDetection:
    """Test header row number detection."""
    
    def test_tsr_file_header(self):
        """Test TSR files have header at row 0."""
        assert get_header_row_number("tsr_1_seg37.csv") == 0
        assert get_header_row_number("TSR_output.npt") == 0
    
    def test_other_file_header(self):
        """Test other files have header at row 2."""
        assert get_header_row_number("2006_Met.npt") == 2
        assert get_header_row_number("flow_data.csv") == 2


class TestFileReading:
    """Test file reading functionality."""
    
    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            read_file("nonexistent_file.npt")
    
    def test_read_sample_file(self, sample_npt_file):
        """Test reading a sample NPT file."""
        if sample_npt_file.exists():
            df = read_file(str(sample_npt_file))
            assert isinstance(df, pd.DataFrame)
            assert not df.empty