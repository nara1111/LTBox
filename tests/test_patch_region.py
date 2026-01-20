import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

from ltbox import constants as const
from ltbox.patch import region as region_patch

class TestRegionPatch:

    @pytest.fixture
    def patterns(self):
        return {
            "row_dot": const.ROW_PATTERN_DOT,
            "prc_dot": const.PRC_PATTERN_DOT,
            "row_i": const.ROW_PATTERN_i if hasattr(const, 'ROW_PATTERN_i') else b'\x00',
        }

    def test_patch_row_to_prc(self):
        input_data = b"PREFIX_" + const.ROW_PATTERN_DOT + b"_SUFFIX"

        if hasattr(region_patch, 'patch_image_content'):
             modified_data, stats = region_patch.patch_image_content(input_data, target_region="PRC")

             assert const.PRC_PATTERN_DOT in modified_data
             assert const.ROW_PATTERN_DOT not in modified_data
             assert stats['changed'] is True

    def test_no_patch_needed(self):
        input_data = b"PREFIX_" + const.PRC_PATTERN_DOT + b"_SUFFIX"

        modified_data, stats = region_patch.patch_image_content(input_data, target_region="PRC")

        assert modified_data == input_data
        assert stats['changed'] is False

    def test_patch_corruption_check(self):
        partial_pattern = const.ROW_PATTERN_DOT[:2]
        input_data = b"DATA_" + partial_pattern + b"_DATA"

        modified_data, stats = region_patch.patch_image_content(input_data, target_region="PRC")

        assert modified_data == input_data
