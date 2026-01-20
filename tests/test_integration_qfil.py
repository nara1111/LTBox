import os
import sys
import shutil
import pytest
import requests
import py7zr
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

from ltbox.patch import avb
from ltbox.actions import xml as xml_action

QFIL_URL = "http://zsk-cdn.lenovows.com/%E7%9F%A5%E8%AF%86%E5%BA%93/Flash_tool_image/TB322_ZUXOS_1.5.10.063_Tool.7z"
QFIL_PASSWORD = os.environ.get("TEST_QFIL_PASSWORD")

CACHE_DIR = Path(__file__).parent / "data"
ARCHIVE_PATH = CACHE_DIR / "qfil_archive.7z"

@pytest.fixture(scope="module")
def real_package(tmp_path_factory):
    if not QFIL_PASSWORD:
        pytest.skip("Skipping integration test: TEST_QFIL_PASSWORD not set")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE_PATH.exists() or ARCHIVE_PATH.stat().st_size == 0:
        print(f"\nDownloading QFIL archive from {QFIL_URL}...")
        try:
            with requests.get(QFIL_URL, stream=True) as r:
                r.raise_for_status()
                with open(ARCHIVE_PATH, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            if ARCHIVE_PATH.exists(): ARCHIVE_PATH.unlink()
            pytest.fail(f"Failed to download QFIL archive: {e}")

    extract_dir = tmp_path_factory.mktemp("real_package")

    target_filenames = [
        "vbmeta.img",
        "boot.img",
        "vendor_boot.img",
        "rawprogram_unsparse0.xml",
        "rawprogram_save_persist_unsparse0.xml"
    ]

    try:
        with py7zr.SevenZipFile(ARCHIVE_PATH, mode='r', password=QFIL_PASSWORD) as z:
            all_files = z.getnames()
            files_to_extract = []

            for fname in all_files:
                normalized_name = fname.replace("\\", "/")

                if "/image/" in normalized_name:
                    basename = os.path.basename(normalized_name)
                    if basename in target_filenames:
                        files_to_extract.append(fname)

            if not files_to_extract:
                pytest.fail("Could not find 'image/' directory or target files in the archive")

            z.extract(path=extract_dir, targets=files_to_extract)

            extracted_map = {}
            for target in target_filenames:
                for path in extract_dir.rglob(target):
                    extracted_map[target] = path
                    break

            return extracted_map

    except Exception as e:
        pytest.fail(f"Failed to extract archive (Check Password?): {e}")

def test_real_vbmeta_parsing(real_package):
    vbmeta_path = real_package.get("vbmeta.img")
    assert vbmeta_path and vbmeta_path.exists()

    info = avb.extract_image_avb_info(vbmeta_path)
    assert info["algorithm"] == "SHA256_RSA4096"
    assert "partition_size" in info

def test_real_boot_parsing(real_package):
    boot_path = real_package.get("boot.img")
    assert boot_path and boot_path.exists()

    info = avb.extract_image_avb_info(boot_path)
    assert int(info["partition_size"]) > int(info["data_size"])

def test_real_xml_wipe_logic(real_package):
    xml_path = real_package.get("rawprogram_unsparse0.xml")
    if not xml_path:
        pytest.skip("rawprogram_unsparse0.xml not found")

    test_xml = xml_path.parent / "test_wipe.xml"
    shutil.copy(xml_path, test_xml)

    from unittest.mock import patch
    with patch("ltbox.actions.xml.utils.ui"):
        xml_action._patch_xml_for_wipe(test_xml, wipe=0)

    tree = ET.parse(test_xml)
    root = tree.getroot()

    userdata_progs = [p for p in root.findall("program") if p.get("label") == "userdata"]
    assert len(userdata_progs) > 0, "No userdata partition found in XML"

    for prog in userdata_progs:
        assert prog.get("filename") == "", f"Userdata filename not cleared: {prog.get('filename')}"

def test_real_xml_save_persist_check(real_package):
    xml_path = real_package.get("rawprogram_save_persist_unsparse0.xml")
    if not xml_path:
        pytest.skip("save_persist xml not found in package")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    persist_prog = next((p for p in root.findall("program") if p.get("label") == "persist"), None)
    if persist_prog:
        filename = persist_prog.get("filename", "")
        assert filename == "", f"Persist should not be flashed in save_persist xml, but found: {filename}"
