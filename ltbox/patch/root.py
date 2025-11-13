import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional, Union

from .. import constants as const
from .. import utils, downloader
from ..i18n import get_string

def patch_boot_with_root_algo(work_dir: Path, magiskboot_exe: Path) -> Optional[Path]:
    original_cwd = Path.cwd()
    os.chdir(work_dir)
    
    patched_boot_path = const.BASE_DIR / "boot.root.img"
    
    try:
        print(get_string("img_root_step1"))
        utils.run_command([str(magiskboot_exe), "unpack", "boot.img"])
        if not (work_dir / "kernel").exists():
            print(get_string("img_root_unpack_fail"))
            return None
        print(get_string("img_root_unpack_ok"))

        print(get_string("img_root_step2"))
        target_kernel_version = get_kernel_version("kernel")

        if not target_kernel_version:
             print(get_string("img_root_kernel_ver_fail"))
             return None

        if not re.match(r"\d+\.\d+\.\d+", target_kernel_version):
             print(get_string("img_root_kernel_invalid").format(ver=target_kernel_version))
             return None
        
        print(get_string("img_root_target_ver").format(ver=target_kernel_version))

        kernel_image_path = downloader.get_gki_kernel(target_kernel_version, work_dir)

        print(get_string("img_root_step5"))
        shutil.move(str(kernel_image_path), "kernel")
        print(get_string("img_root_kernel_replaced"))

        print(get_string("img_root_step6"))
        utils.run_command([str(magiskboot_exe), "repack", "boot.img"])
        if not (work_dir / "new-boot.img").exists():
            print(get_string("img_root_repack_fail"))
            return None
        shutil.move("new-boot.img", patched_boot_path)
        print(get_string("img_root_repack_ok"))

        downloader.download_ksu_apk(const.BASE_DIR)
        
        return patched_boot_path

    finally:
        os.chdir(original_cwd)
        if work_dir.exists():
            shutil.rmtree(work_dir)
        print(get_string("img_root_cleanup"))

def get_kernel_version(file_path: Union[str, Path]) -> Optional[str]:
    kernel_file = Path(file_path)
    if not kernel_file.exists():
        print(get_string("img_kv_err_not_found").format(path=file_path), file=sys.stderr)
        return None

    try:
        content = kernel_file.read_bytes()
        potential_strings = re.findall(b'[ -~]{10,}', content)
        
        found_version = None
        for string_bytes in potential_strings:
            try:
                line = string_bytes.decode('ascii', errors='ignore')
                if 'Linux version ' in line:
                    base_version_match = re.search(r'(\d+\.\d+\.\d+)', line)
                    if base_version_match:
                        found_version = base_version_match.group(1)
                        print(get_string("img_kv_found").format(line=line.strip()), file=sys.stderr)
                        break
            except UnicodeDecodeError:
                continue

        if found_version:
            return found_version
        else:
            print(get_string("img_kv_err_parse"), file=sys.stderr)
            return None

    except Exception as e:
        print(get_string("img_kv_err_unexpected").format(e=e), file=sys.stderr)
        return None