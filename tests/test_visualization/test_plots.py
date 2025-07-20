"""Tests for CE-QUAL-W2 visualization functionality."""

import pytest
import pandas as pd
import matplotlib.pyplot as plt

from cequalw2.visualization.plots import get_colors


class TestColorPalettes:
    """Test color palette functionality."""
    
    def test_get_colors_default(self, sample_dataframe):
        """Test getting colors with default parameters."""
        colors = get_colors(sample_dataframe, "rainbow")
        assert isinstance(colors, list)
        assert len(colors) >= 6  # Default minimum colors
    
    def test_get_colors_min_colors(self, sample_dataframe):
        """Test getting colors with minimum color requirement."""
        colors = get_colors(sample_dataframe, "everest", min_colors=10)
        assert len(colors) >= 10