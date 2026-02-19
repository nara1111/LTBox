from unittest.mock import MagicMock, patch

import pytest
from ltbox.actions import edl


def test_collect_flashable_partitions_from_xml(mock_env):
    img_dir = mock_env["IMAGE_DIR"]
    (img_dir / "rawprogram0.xml").write_text(
        """<?xml version='1.0'?><data>
        <program label='boot' filename='boot.img' physical_partition_number='0' start_sector='100'/>
        <program label='boot' filename='boot_1.img' physical_partition_number='0' start_sector='200'/>
        <program label='persist' filename='' physical_partition_number='0' start_sector='300'/>
        </data>""",
        encoding="utf-8",
    )

    with patch("ltbox.actions.edl.xml.ensure_xml_files"):
        part_map = edl._collect_flashable_partitions()

    assert sorted(part_map.keys()) == ["boot"]
    assert [x["filename"] for x in part_map["boot"]] == ["boot.img", "boot_1.img"]


def test_flash_partition_labels_fails_when_image_missing(mock_env):
    img_dir = mock_env["IMAGE_DIR"]
    (img_dir / "rawprogram0.xml").write_text(
        """<?xml version='1.0'?><data>
        <program label='boot' filename='boot.img' physical_partition_number='0' start_sector='100'/>
        </data>""",
        encoding="utf-8",
    )

    with patch("ltbox.actions.edl.xml.ensure_xml_files"), patch(
        "ltbox.actions.edl._prompt_partition_selection", return_value=["boot"]
    ):
        with pytest.raises(FileNotFoundError):
            edl.flash_partition_labels(MagicMock())


def test_flash_partition_labels_writes_selected_entries(mock_env):
    img_dir = mock_env["IMAGE_DIR"]
    (img_dir / "rawprogram0.xml").write_text(
        """<?xml version='1.0'?><data>
        <program label='super' filename='super_1.img' physical_partition_number='0' start_sector='100'/>
        <program label='super' filename='super_2.img' physical_partition_number='0' start_sector='200'/>
        </data>""",
        encoding="utf-8",
    )
    (img_dir / "super_1.img").write_text("a", encoding="utf-8")
    (img_dir / "super_2.img").write_text("b", encoding="utf-8")

    dev = MagicMock()

    with patch("ltbox.actions.edl.xml.ensure_xml_files"), patch(
        "ltbox.actions.edl._prompt_partition_selection", return_value=["super"]
    ), patch("ltbox.actions.edl._prepare_edl_session", return_value="COM1"):
        edl.flash_partition_labels(dev, skip_reset=True)

    assert dev.edl.write_partition.call_count == 2
    dev.edl.reset.assert_not_called()
