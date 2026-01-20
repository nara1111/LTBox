import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

from ltbox.actions import xml as xml_action

@pytest.fixture
def mock_xml_env(tmp_path):
    dirs = {
        "IMAGE_DIR": tmp_path / "image",
        "OUTPUT_XML_DIR": tmp_path / "output_xml",
        "WORKING_DIR": tmp_path / "working"
    }
    for d in dirs.values():
        d.mkdir()

    with patch.multiple("ltbox.actions.xml.const", **dirs):
        yield dirs

class TestActions:
    def test_rawprogram_fallback_priority(self, mock_xml_env):
        dirs = mock_xml_env
        output_dir = dirs["OUTPUT_XML_DIR"]
        target_file = output_dir / "rawprogram_save_persist_unsparse0.xml"

        cases = [
            (
                ["rawprogram_unsparse0.xml", "rawprogram0.xml"],
                "rawprogram_unsparse0.xml",
                "MARKER_UNSPARSE"
            ),
            (
                ["rawprogram0.xml"],
                "rawprogram0.xml",
                "MARKER_BASIC"
            )
        ]

        xml_template = """<?xml version="1.0" ?><data><program label="{marker}" filename=""/></data>"""

        for filenames, expected_choice, marker in cases:
            if target_file.exists(): target_file.unlink()
            for f in output_dir.glob("*.xml"): f.unlink()

            for fname in filenames:
                content_marker = marker if fname == expected_choice else "WRONG_FILE"
                (output_dir / fname).write_text(xml_template.format(marker=content_marker))

            with patch("ltbox.actions.xml.utils.ui"):
                xml_action._ensure_rawprogram_save_persist(output_dir)

            assert target_file.exists()
            tree = ET.parse(target_file)
            root = tree.getroot()
            prog = root.find("program")
            assert prog.get("label") == marker, f"Failed to pick {expected_choice} among {filenames}"

    def test_decrypt_workflow(self, mock_xml_env):
        dirs = mock_xml_env
        (dirs["IMAGE_DIR"] / "test.x").write_text("encrypted")

        with patch("ltbox.actions.xml.utils.ui"), \
             patch("ltbox.actions.xml.utils.wait_for_directory"), \
             patch("ltbox.actions.xml.decrypt_file", return_value=True):

            xml_action.decrypt_x_files()

    def test_xml_wipe_logic(self, mock_xml_env):
        dirs = mock_xml_env
        xml_path = dirs["OUTPUT_XML_DIR"] / "rawprogram_save_persist_unsparse0.xml"

        root = ET.Element("data")
        ET.SubElement(root, "program", label="userdata", filename="userdata.img")
        tree = ET.ElementTree(root)
        tree.write(xml_path)

        with patch("ltbox.actions.xml.utils.ui"):
            xml_action._patch_xml_for_wipe(xml_path, wipe=0)

        tree = ET.parse(xml_path)
        prog = tree.find(".//program[@label='userdata']")
        assert prog.attrib["filename"] == ""

    def test_region_patch_patterns(self):
        if not region_patch:
            pytest.skip("Region patch module not found")

        row_pat = const.ROW_PATTERN_DOT
        prc_pat = const.PRC_PATTERN_DOT

        if not row_pat or not prc_pat:
            pytest.skip("Patterns not defined in constants")

        data = b"PRE" + row_pat + b"SUF"

        if hasattr(region_patch, "patch_image_content"):
            new_data, stats = region_patch.patch_image_content(data, target_region="PRC")
            assert prc_pat in new_data
            assert stats["changed"] is True
