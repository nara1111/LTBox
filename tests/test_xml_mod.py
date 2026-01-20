import sys
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

from ltbox.actions import xml as xml_action

MINIMAL_RAW0_XML = """<?xml version="1.0" encoding="utf-8"?>
<data>
  <program label="proinfo" filename="" />
  <program label="persist" filename="persist.img" />
  <program label="metadata" filename="metadata.img" />
  <program label="userdata" filename="userdata.img" />
  <program label="super" filename="super.img" />
</data>
"""

MINIMAL_RAW4_XML = """<?xml version="1.0" encoding="utf-8"?>
<data>
  <program label="devinfo" filename="devinfo_original.img" />
</data>
"""

@pytest.fixture
def mock_dirs(tmp_path):
    image_dir = tmp_path / "image"
    image_dir.mkdir()

    output_xml_dir = tmp_path / "output_xml"
    output_xml_dir.mkdir()

    working_dir = tmp_path / "working"
    working_dir.mkdir()

    with patch("ltbox.actions.xml.const.IMAGE_DIR", image_dir), \
         patch("ltbox.actions.xml.const.OUTPUT_XML_DIR", output_xml_dir), \
         patch("ltbox.actions.xml.const.WORKING_DIR", working_dir):
        yield image_dir, output_xml_dir, working_dir

def get_xml_filename(xml_path, label):
    if not xml_path.exists():
        return None
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for prog in root.findall("program"):
        if prog.get("label", "").lower() == label.lower():
            return prog.get("filename", "")
    return None

class TestXmlModification:

    def test_fallback_recognition_and_persist_clearing(self, mock_dirs):
        _, output_xml_dir, _ = mock_dirs

        fallback_file = output_xml_dir / "rawprogram_unsparse0.xml"
        fallback_file.write_text(MINIMAL_RAW0_XML, encoding="utf-8")

        with patch("ltbox.actions.xml.utils.ui"):
            xml_action._ensure_rawprogram_save_persist(output_xml_dir)

        target_file = output_xml_dir / "rawprogram_save_persist_unsparse0.xml"

        assert target_file.exists()

        persist_fname = get_xml_filename(target_file, "persist")
        assert persist_fname == "", "For save_persist xml, the persist file name must be empty."

    @pytest.mark.parametrize("wipe_mode, expect_userdata", [
        (0, ""),
        (1, "userdata.img"),
    ])
    def test_wipe_options(self, mock_dirs, wipe_mode, expect_userdata):
        _, output_xml_dir, _ = mock_dirs

        target_file = output_xml_dir / "rawprogram_save_persist_unsparse0.xml"
        target_file.write_text(MINIMAL_RAW0_XML, encoding="utf-8")

        with patch("ltbox.actions.xml.utils.ui"):
            xml_action._patch_xml_for_wipe(target_file, wipe=wipe_mode)

        assert get_xml_filename(target_file, "userdata") == expect_userdata
        assert get_xml_filename(target_file, "metadata") == expect_userdata

        assert get_xml_filename(target_file, "super") == "super.img"

    def test_modify_xml_full_flow(self, mock_dirs):
        _, output_xml_dir, _ = mock_dirs

        (output_xml_dir / "rawprogram_unsparse0.xml").write_text(MINIMAL_RAW0_XML, encoding="utf-8")
        (output_xml_dir / "rawprogram_unsparse4.xml").write_text(MINIMAL_RAW4_XML, encoding="utf-8")

        with patch("ltbox.actions.xml.utils.ui"), \
             patch("ltbox.actions.xml.utils.temporary_workspace") as mock_workspace:
            mock_workspace.return_value.__enter__.return_value = None

            xml_action.modify_xml(wipe=0, skip_dp=False)

        save_xml = output_xml_dir / "rawprogram_save_persist_unsparse0.xml"
        assert save_xml.exists()
        assert get_xml_filename(save_xml, "persist") == ""
        assert get_xml_filename(save_xml, "userdata") == ""

        write_persist_xml = output_xml_dir / "rawprogram_write_persist_unsparse0.xml"
        assert write_persist_xml.exists()
        assert get_xml_filename(write_persist_xml, "persist") == "persist.img"

        raw4_xml = output_xml_dir / "rawprogram4.xml"
        assert raw4_xml.exists()
        assert get_xml_filename(raw4_xml, "devinfo") == ""

        write_devinfo_xml = output_xml_dir / "rawprogram4_write_devinfo.xml"
        assert write_devinfo_xml.exists()
        assert get_xml_filename(write_devinfo_xml, "devinfo") == "devinfo.img"
