import os
import shutil
import sys
import time
from pathlib import Path
from pypdl import Pypdl
from unittest.mock import patch

import py7zr
import pytest
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin')))

QFIL_URL = "http://zsk-cdn.lenovows.com/%E7%9F%A5%E8%AF%86%E5%BA%93/Flash_tool_image/TB322_ZUXOS_1.5.10.063_Tool.7z"
QFIL_PW = os.environ.get("TEST_QFIL_PASSWORD")
CACHE_DIR = Path(__file__).parent / "data"
ARCHIVE = CACHE_DIR / "qfil_archive.7z"

@pytest.fixture(autouse=True)
def mock_python_executable():
    with patch("ltbox.constants.PYTHON_EXE", sys.executable):
        yield

@pytest.fixture(scope="module")
def fw_pkg(tmp_path_factory):
    if not QFIL_PW:
        pytest.skip("TEST_QFIL_PASSWORD not set")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not ARCHIVE.exists() or ARCHIVE.stat().st_size == 0:
        print(f"\n[INFO] Starting download...", flush=True)
        try:
            is_ci = os.environ.get("CI", "false").lower() == "true" or \
                    os.environ.get("GITHUB_ACTIONS", "false").lower() == "true"

            dl = Pypdl()
            dl.start(
                QFIL_URL,
                file_path=str(ARCHIVE),
                segments=10,
                display=not is_ci,
                multithread=True,
                block=True,
                retries=3
            )
            print(f"\n[INFO] Download Complete! Size: {ARCHIVE.stat().st_size / (1024**3):.2f} GB", flush=True)

        except Exception as e:
            if ARCHIVE.exists(): ARCHIVE.unlink()
            pytest.fail(f"Download failed: {e}")

    extract_dir = tmp_path_factory.mktemp("pkg")
    targets = ["vbmeta.img", "boot.img", "vendor_boot.img",
               "rawprogram_unsparse0.xml", "rawprogram_save_persist_unsparse0.xml"]

    try:
        print("[INFO] Extracting...", flush=True)
        with py7zr.SevenZipFile(ARCHIVE, mode='r', password=QFIL_PW) as z:
            all_f = z.getnames()
            to_ext = [f for f in all_f if os.path.basename(f.replace("\\", "/")) in targets and "/image/" in f.replace("\\", "/")]

            if not to_ext: pytest.fail("Targets not found")
            z.extract(path=extract_dir, targets=to_ext)

            mapped = {}
            for t in targets:
                for p in extract_dir.rglob(t):
                    mapped[t] = p
                    break
            return mapped
    except Exception as e:
        pytest.fail(f"Extraction failed: {e}")

@pytest.fixture
def mock_env(tmp_path):
    dirs = {
        "IMAGE_DIR": tmp_path / "image",
        "OUTPUT_DP_DIR": tmp_path / "output_dp",
        "OUTPUT_DIR": tmp_path / "output",
        "OUTPUT_ANTI_ROLLBACK_DIR": tmp_path / "output_arb",
        "OUTPUT_XML_DIR": tmp_path / "output_xml",
        "EDL_LOADER_FILE": tmp_path / "loader.elf"
    }
    for d in dirs.values():
        if d.suffix:
            d.parent.mkdir(parents=True, exist_ok=True)
            d.touch()
        else:
            d.mkdir(parents=True, exist_ok=True)

    with patch.multiple("ltbox.constants", **dirs):
        yield dirs
