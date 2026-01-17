import sys
import shutil
import zipfile
import re
from pathlib import Path
from typing import Optional, Dict, Any

from .. import constants as const
from .. import utils, downloader, i18n
from ..utils import ui
from ..i18n import get_string
from ..patch.root import patch_boot_image
from ..errors import LTBoxError, UserCancelError

def _cleanup_manager_apk():
    manager_apk = const.TOOLS_DIR / "manager.apk"
    if manager_apk.exists():
        manager_apk.unlink()

def _get_mapped_kernel_name(kernel_version: str) -> Optional[str]:
    if not kernel_version:
        return None
        
    major_minor = ".".join(kernel_version.split(".")[:2])
    mapping = {
        "5.10": "android12-5.10",
        "5.15": "android13-5.15",
        "6.1":  "android14-6.1",
        "6.6":  "android15-6.6",
        "6.12": "android16-6.12"
    }
    return mapping.get(major_minor)

def _prompt_workflow(root_name: str, default_id: str) -> str:
    msg_enter = get_string("prompt_workflow_id").replace("{name}", root_name)
    msg_default = get_string("prompt_workflow_default").replace("{id}", default_id)
    
    ui.echo("-" * 60)
    ui.echo(msg_enter)
    ui.echo(msg_default)
    ui.echo("-" * 60)
    
    val = input("Input > ").strip()
    if not val:
        return default_id
    return val

def _handle_nightly_download(root_name: str, repo: str, default_workflow: str, manager_zip_name: str, kernel_version: str) -> bool:
    mapped_name = _get_mapped_kernel_name(kernel_version)
    if not mapped_name:
        ui.error(get_string("err_sukisu_kernel_map_not_found").format(ver=kernel_version))
        return False

    while True:
        workflow_id = _prompt_workflow(root_name, default_workflow)
        
        try:
            downloader.download_nightly_artifacts(
                repo=repo,
                workflow_id=workflow_id,
                manager_name=manager_zip_name,
                mapped_name=mapped_name,
                target_dir=const.TOOLS_DIR
            )
            
            manager_zip = const.TOOLS_DIR / manager_zip_name
            apk_extracted = False
            if manager_zip.exists():
                with zipfile.ZipFile(manager_zip, 'r') as zf:
                    for name in zf.namelist():
                        if name.endswith(".apk"):
                            with zf.open(name) as source, open(const.TOOLS_DIR / "manager.apk", "wb") as target:
                                shutil.copyfileobj(source, target)
                            apk_extracted = True
                            break
                manager_zip.unlink()
            
            if not apk_extracted:
                ui.error("Failed to find APK in manager zip.")
                raise RuntimeError("Manager APK missing")

            lkm_zip = const.TOOLS_DIR / "lkm.zip"
            ko_extracted = False
            if lkm_zip.exists():
                with zipfile.ZipFile(lkm_zip, 'r') as zf:
                    for name in zf.namelist():
                        if name.endswith("_kernelsu.ko") or name.endswith("kernelsu.ko"):
                            with zf.open(name) as source, open(const.TOOLS_DIR / "kernelsu.ko", "wb") as target:
                                shutil.copyfileobj(source, target)
                            ko_extracted = True
                            break
                lkm_zip.unlink()

            if not ko_extracted:
                ui.error("Failed to find kernelsu.ko in lkm.zip")
                raise RuntimeError("LKM missing")

            return True
            
        except Exception as e:
            ui.error(f"{e}")
            ui.error(get_string("err_download_workflow"))

            return False

def prepare_root_files(dev, gki: bool, root_type: str) -> bool:
    _cleanup_manager_apk()
    
    if gki:
        downloader.download_gki_tools(gki=True)
        return True

    kernel_version = None
    if not dev.skip_adb:
        try:
            kernel_version = dev.get_kernel_version()
        except Exception:
            pass
    
    if not kernel_version:
        ui.echo(get_string("err_req_kernel_ver_lkm"))
        kernel_version = input("Enter Kernel Version (e.g. 5.15.100): ").strip()
        if not kernel_version:
            return False

    settings = const.load_settings_raw()

    if root_type == "ksu":
        from ..main import TerminalMenu
        
        menu = TerminalMenu(get_string("menu_root_subtype_title"))
        menu.add_option("1", get_string("menu_root_subtype_release"))
        menu.add_option("2", get_string("menu_root_subtype_nightly"))

        while True:
            choice = menu.ask(get_string("menu_root_subtype_prompt"), get_string("menu_invalid"))
            
            if choice == "1":
                downloader.download_ksu_manager_release(const.TOOLS_DIR)
                downloader.download_ksuinit_release(const.TOOLS_DIR / "ksuinit")
                downloader.get_lkm_kernel_release(const.TOOLS_DIR / "kernelsu.ko", kernel_version)
                return True
                
            elif choice == "2":
                conf = settings.get("kernelsu-next", {})
                success = _handle_nightly_download(
                    root_name="KernelSU Next",
                    repo=conf.get("repo"),
                    default_workflow=conf.get("nightly_workflow"),
                    manager_zip_name=conf.get("nightly_manager"),
                    kernel_version=kernel_version
                )
                if success:
                    return True
            
    elif root_type == "sukisu":
        conf = settings.get("sukisu-ultra", {})
        success = _handle_nightly_download(
            root_name="SukiSU Ultra",
            repo=conf.get("repo"),
            default_workflow=conf.get("workflow"),
            manager_zip_name=conf.get("manager"),
            kernel_version=kernel_version
        )
        return success

    return False

def root_device(dev, gki: bool = False, root_type: str = "ksu"):
    if not prepare_root_files(dev, gki, root_type):
        return

    ui.info(get_string("act_wait_image"))
    const.IMAGE_DIR.mkdir(exist_ok=True)
    
    boot_img = const.IMAGE_DIR / "boot.img"
    init_boot_img = const.IMAGE_DIR / "init_boot.img"

    target_image = boot_img
    if init_boot_img.exists():
        target_image = init_boot_img
    elif not boot_img.exists():
        utils.wait_for_file(boot_img, get_string("act_prompt_boot_image"))
        target_image = boot_img

    ui.info(get_string("act_patching"))

    patch_boot_image(target_image, gki=gki)

    ui.info(get_string("act_flashing"))
    if not dev.skip_adb:
        pass
    else:
        ui.info("ADB skipped. Please flash the patched image manually.")

def patch_root_image_file(dev, gki: bool = False, root_type: str = "ksu"):
    if not prepare_root_files(dev, gki, root_type):
        return

    ui.info(get_string("act_drag_drop_boot"))
    
    target_path = Path(input("Enter path to boot/init_boot image: ").strip().strip('"'))
    if not target_path.exists():
        ui.error(get_string("err_file_not_found"))
        return

    ui.info(get_string("act_patching"))
    patch_boot_image(target_path, gki=gki)
    ui.info(get_string("act_success"))