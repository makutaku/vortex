"""
Tests for core constants functionality.
"""

import pytest

from vortex.constants import ProviderConstants, get_provider_constants


class TestGetProviderConstants:
    """Test provider constants retrieval functionality."""
    
    def test_get_provider_constants_barchart(self):
        """Test getting Barchart provider constants."""
        constants = get_provider_constants('barchart')
        
        assert isinstance(constants, dict)
        assert 'MIN_REQUIRED_DATA_POINTS' in constants
        assert constants['MIN_REQUIRED_DATA_POINTS'] == ProviderConstants.Barchart.MIN_REQUIRED_DATA_POINTS
    
    def test_get_provider_constants_yahoo(self):
        """Test getting Yahoo provider constants."""
        constants = get_provider_constants('yahoo')
        
        assert isinstance(constants, dict)
        assert 'MAX_SYMBOLS_PER_REQUEST' in constants
        assert constants['MAX_SYMBOLS_PER_REQUEST'] == ProviderConstants.Yahoo.MAX_SYMBOLS_PER_REQUEST
    
    def test_get_provider_constants_ibkr(self):
        """Test getting IBKR provider constants."""
        constants = get_provider_constants('ibkr')
        
        assert isinstance(constants, dict)
        assert 'DEFAULT_CLIENT_ID' in constants
        assert constants['DEFAULT_CLIENT_ID'] == ProviderConstants.IBKR.DEFAULT_CLIENT_ID
    
    def test_get_provider_constants_case_insensitive(self):
        """Test that provider names are case insensitive."""
        constants_lower = get_provider_constants('barchart')
        constants_upper = get_provider_constants('BARCHART')
        constants_mixed = get_provider_constants('BarchArt')
        
        assert constants_lower == constants_upper == constants_mixed
    
    def test_get_provider_constants_unknown_provider(self):
        """Test handling of unknown provider names."""
        with pytest.raises(ValueError, match="Unknown provider: nonexistent"):
            get_provider_constants('nonexistent')
    
    def test_get_provider_constants_excludes_private_attributes(self):
        """Test that private attributes (starting with _) are excluded."""
        constants = get_provider_constants('barchart')
        
        # Should not contain any keys starting with underscore
        private_keys = [key for key in constants.keys() if key.startswith('_')]
        assert len(private_keys) == 0
    
    def test_get_provider_constants_all_providers_have_constants(self):
        """Test that all supported providers return non-empty constants."""
        providers = ['barchart', 'yahoo', 'ibkr']
        
        for provider in providers:
            constants = get_provider_constants(provider)
            assert isinstance(constants, dict)
            assert len(constants) > 0
    
    def test_get_provider_constants_returns_copy_of_attributes(self):
        """Test that returned constants are based on class attributes."""
        constants = get_provider_constants('barchart')
        
        # Verify it contains expected attributes from the class
        barchart_class_attrs = [
            attr for attr in dir(ProviderConstants.Barchart) 
            if not attr.startswith('_')
        ]
        
        for attr in barchart_class_attrs:
            if not callable(getattr(ProviderConstants.Barchart, attr)):
                assert attr in constants