import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch, MagicMock

from vortex.utils.utils import (
    random_sleep,
    create_full_path,
    get_first_and_last_day_of_years,
    date_range_generator,
    reverse_date_range_generator,
    convert_date_strings_to_datetime,
    is_list_of_strings,
    merge_dicts,
    get_absolute_path,
    total_elements_in_dict_of_lists,
    generate_year_month_tuples
)
from vortex.models.period import Period


class TestRandomSleep:
    @patch('vortex.utils.utils.time.sleep')
    @patch('vortex.utils.utils.randint')
    def test_random_sleep_default(self, mock_randint, mock_sleep):
        """Test random_sleep with default parameter."""
        mock_randint.return_value = 5
        
        random_sleep()
        
        mock_randint.assert_called_once_with(1, 16)  # 1 + 15
        mock_sleep.assert_called_once_with(5)

    @patch('vortex.utils.utils.time.sleep')
    @patch('vortex.utils.utils.randint')
    def test_random_sleep_custom_param(self, mock_randint, mock_sleep):
        """Test random_sleep with custom parameter."""
        mock_randint.return_value = 3
        
        random_sleep(10)
        
        mock_randint.assert_called_once_with(1, 11)  # 1 + 10
        mock_sleep.assert_called_once_with(3)


class TestCreateFullPath:
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_full_path_existing_directory(self):
        """Test create_full_path with existing directory."""
        existing_dir = tempfile.mkdtemp()
        file_path = os.path.join(existing_dir, 'test.txt')
        
        result = create_full_path(file_path)
        
        assert result == file_path
        assert os.path.exists(existing_dir)
        
        # Cleanup
        shutil.rmtree(existing_dir)

    def test_create_full_path_new_directory(self):
        """Test create_full_path with new directory."""
        temp_dir = tempfile.mkdtemp()
        new_dir = os.path.join(temp_dir, 'new_subdir', 'nested')
        file_path = os.path.join(new_dir, 'test.txt')
        
        result = create_full_path(file_path)
        
        assert result == file_path
        assert os.path.exists(new_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_create_full_path_file_only(self):
        """Test create_full_path with file in current directory."""
        file_path = './test.txt'  # Use explicit current directory
        
        result = create_full_path(file_path)
        
        assert result == file_path


class TestGetFirstAndLastDayOfYears:
    def test_single_year(self):
        """Test with single year."""
        start, end = get_first_and_last_day_of_years(2024, 2024)
        
        assert start == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert end == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    def test_multiple_years(self):
        """Test with multiple years."""
        start, end = get_first_and_last_day_of_years(2022, 2024)
        
        assert start == datetime(2022, 1, 1, tzinfo=timezone.utc)
        assert end == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    def test_custom_timezone(self):
        """Test with custom timezone."""
        import pytz
        est = pytz.timezone('US/Eastern')
        
        start, end = get_first_and_last_day_of_years(2023, 2023, tz=est)
        
        assert start.tzinfo == est
        assert end.tzinfo == est
        assert start.year == 2023
        assert end.year == 2023


class TestDateRangeGenerator:
    def test_date_range_generator_basic(self):
        """Test basic date range generation."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        delta = timedelta(days=3)
        
        ranges = list(date_range_generator(start, end, delta))
        
        expected = [
            (datetime(2024, 1, 1), datetime(2024, 1, 4)),
            (datetime(2024, 1, 4), datetime(2024, 1, 7)),
            (datetime(2024, 1, 7), datetime(2024, 1, 10))
        ]
        
        assert ranges == expected

    def test_date_range_generator_no_delta(self):
        """Test date range generation with None delta."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        
        ranges = list(date_range_generator(start, end, None))
        
        assert ranges == [(start, end)]

    def test_date_range_generator_invalid_order(self):
        """Test date range generation with start > end."""
        start = datetime(2024, 1, 10)
        end = datetime(2024, 1, 1)
        delta = timedelta(days=1)
        
        with pytest.raises(ValueError, match="start_date must come before end_date"):
            list(date_range_generator(start, end, delta))

    def test_date_range_generator_exact_fit(self):
        """Test date range generation where delta fits exactly."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 7)
        delta = timedelta(days=3)
        
        ranges = list(date_range_generator(start, end, delta))
        
        expected = [
            (datetime(2024, 1, 1), datetime(2024, 1, 4)),
            (datetime(2024, 1, 4), datetime(2024, 1, 7))
        ]
        
        assert ranges == expected


class TestReverseDateRangeGenerator:
    def test_reverse_date_range_generator_basic(self):
        """Test basic reverse date range generation."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        delta = timedelta(days=3)
        
        ranges = list(reverse_date_range_generator(start, end, delta))
        
        expected = [
            (datetime(2024, 1, 7), datetime(2024, 1, 10)),
            (datetime(2024, 1, 4), datetime(2024, 1, 7)),
            (datetime(2024, 1, 1), datetime(2024, 1, 4))
        ]
        
        assert ranges == expected

    def test_reverse_date_range_generator_no_delta(self):
        """Test reverse date range generation with None delta."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        
        ranges = list(reverse_date_range_generator(start, end, None))
        
        assert ranges == [(start, end)]


class TestConvertDateStringsToDatetime:
    def test_convert_date_strings_basic(self):
        """Test basic date string conversion."""
        input_dict = {
            'start_date': '2024-01-01T00:00:00Z',
            'end_date': '2024-01-10T00:00:00Z',
            'other_field': 'not_a_date'
        }
        
        result = convert_date_strings_to_datetime(input_dict)
        
        assert isinstance(result['start_date'], datetime)
        assert isinstance(result['end_date'], datetime)
        assert result['other_field'] == 'not_a_date'
        assert result['start_date'].tzinfo == timezone.utc
        assert result['end_date'].tzinfo == timezone.utc

    def test_convert_date_strings_with_period(self):
        """Test conversion with period field."""
        input_dict = {
            'start_date': '2024-01-01T00:00:00Z',
            'period': '1d'
        }
        
        result = convert_date_strings_to_datetime(input_dict)
        
        assert isinstance(result['start_date'], datetime)
        assert isinstance(result['period'], Period)

    def test_convert_date_strings_invalid_date(self):
        """Test conversion with invalid date string."""
        input_dict = {
            'start_date': 'invalid_date',
            'end_date': '2024-01-10T00:00:00Z'
        }
        
        with patch('vortex.utils.utils.logging.warning') as mock_warning:
            result = convert_date_strings_to_datetime(input_dict)
            
            mock_warning.assert_called()
            assert result['start_date'] == 'invalid_date'  # Should remain unchanged
            assert isinstance(result['end_date'], datetime)

    def test_convert_date_strings_none_values(self):
        """Test conversion with None values."""
        input_dict = {
            'start_date': None,
            'period': None,
            'other_field': 'value'
        }
        
        result = convert_date_strings_to_datetime(input_dict)
        
        assert result['start_date'] is None
        assert result['period'] is None
        assert result['other_field'] == 'value'


class TestIsListOfStrings:
    def test_is_list_of_strings_true(self):
        """Test with valid list of strings."""
        assert is_list_of_strings(['a', 'b', 'c']) is True
        assert is_list_of_strings(['']) is True
        assert is_list_of_strings([]) is True

    def test_is_list_of_strings_false(self):
        """Test with invalid inputs."""
        assert is_list_of_strings(['a', 1, 'c']) is False
        assert is_list_of_strings([1, 2, 3]) is False
        assert is_list_of_strings('not_a_list') is False
        assert is_list_of_strings(None) is False
        assert is_list_of_strings(['a', None, 'c']) is False


class TestMergeDicts:
    def test_merge_dicts_basic(self):
        """Test basic dictionary merging."""
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'c': 3, 'd': 4}
        dict3 = {'e': 5}
        
        result = merge_dicts([dict1, dict2, dict3])
        
        expected = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
        assert result == expected

    def test_merge_dicts_duplicate_key(self):
        """Test merging with duplicate keys."""
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'b': 3, 'c': 4}  # 'b' is duplicate
        
        with pytest.raises(ValueError, match="Duplicate key found: b"):
            merge_dicts([dict1, dict2])

    def test_merge_dicts_empty_list(self):
        """Test merging empty list."""
        result = merge_dicts([])
        assert result == {}

    def test_merge_dicts_single_dict(self):
        """Test merging single dictionary."""
        dict1 = {'a': 1, 'b': 2}
        result = merge_dicts([dict1])
        assert result == dict1


class TestGetAbsolutePath:
    def test_get_absolute_path_relative(self):
        """Test converting relative path to absolute."""
        result = get_absolute_path('.')
        assert os.path.isabs(result)

    def test_get_absolute_path_home(self):
        """Test expanding home directory."""
        result = get_absolute_path('~/test')
        assert os.path.isabs(result)
        assert '~' not in result

    def test_get_absolute_path_absolute(self):
        """Test with already absolute path."""
        abs_path = os.path.abspath('/tmp')
        result = get_absolute_path(abs_path)
        assert result == abs_path


class TestTotalElementsInDictOfLists:
    def test_total_elements_basic(self):
        """Test basic counting of elements."""
        test_dict = {
            'list1': ['a', 'b', 'c'],
            'list2': ['d', 'e'],
            'list3': ['f']
        }
        
        result = total_elements_in_dict_of_lists(test_dict)
        assert result == 6

    def test_total_elements_empty_dict(self):
        """Test with empty dictionary."""
        result = total_elements_in_dict_of_lists({})
        assert result == 0

    def test_total_elements_none_dict(self):
        """Test with None dictionary."""
        result = total_elements_in_dict_of_lists(None)
        assert result == 0

    def test_total_elements_empty_lists(self):
        """Test with empty lists."""
        test_dict = {
            'list1': [],
            'list2': [],
            'list3': ['a']
        }
        
        result = total_elements_in_dict_of_lists(test_dict)
        assert result == 1

    def test_total_elements_non_list_value(self):
        """Test with non-list values."""
        test_dict = {
            'list1': ['a', 'b'],
            'not_list': 'string'
        }
        
        with pytest.raises(ValueError, match="Dictionary values must be lists"):
            total_elements_in_dict_of_lists(test_dict)


class TestGenerateYearMonthTuples:
    def test_generate_year_month_tuples_same_month(self):
        """Test with same month."""
        start = date(2024, 3, 15)
        end = date(2024, 3, 25)
        
        result = list(generate_year_month_tuples(start, end))
        
        assert result == [(2024, 3)]

    def test_generate_year_month_tuples_multiple_months(self):
        """Test with multiple months."""
        start = date(2024, 1, 15)
        end = date(2024, 4, 10)
        
        result = list(generate_year_month_tuples(start, end))
        
        expected = [(2024, 1), (2024, 2), (2024, 3), (2024, 4)]
        assert result == expected

    def test_generate_year_month_tuples_year_boundary(self):
        """Test crossing year boundary."""
        start = date(2023, 11, 15)
        end = date(2024, 2, 10)
        
        result = list(generate_year_month_tuples(start, end))
        
        expected = [(2023, 11), (2023, 12), (2024, 1), (2024, 2)]
        assert result == expected

    def test_generate_year_month_tuples_datetime_input(self):
        """Test with datetime objects."""
        start = datetime(2024, 6, 15, 10, 30)
        end = datetime(2024, 8, 10, 14, 45)
        
        result = list(generate_year_month_tuples(start, end))
        
        expected = [(2024, 6), (2024, 7), (2024, 8)]
        assert result == expected

    def test_generate_year_month_tuples_december_year_change(self):
        """Test December to January transition."""
        start = date(2023, 12, 1)
        end = date(2024, 1, 15)
        
        result = list(generate_year_month_tuples(start, end))
        
        expected = [(2023, 12), (2024, 1)]
        assert result == expected