import platform
import subprocess
import sys
import time
import zipfile
import shutil

from ltbox.constants import *
from ltbox import utils

def _ensure_edl_ng():
    if platform.system() != "Windows":
        print("[!] EDL functions are only supported on Windows.", file=sys.stderr)
        sys.exit(1)
        
    edl_ng_exe = TOOLS_DIR / "edl-ng.exe"
    if edl_ng_exe.exists():
        return edl_ng_exe

    fetch_exe = utils.get_platform_executable("fetch")
    if not fetch_exe.exists():
         print(f"[!] '{fetch_exe.name}' not found. Please run install.bat")
         sys.exit(1)

    print(f"[!] '{edl_ng_exe.name}' not found. Attempting to download...")
    arch = platform.machine()
    if arch == 'AMD64':
        asset_pattern = "edl-ng-windows-x64.zip"
    elif arch == 'ARM64':
        asset_pattern = "edl-ng-windows-arm64.zip"
    else:
        print(f"[!] Unsupported Windows architecture: {arch}. Cannot download edl-ng.", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Detected {arch} architecture. Downloading '{asset_pattern}'...")

    try:
        fetch_command = [
            str(fetch_exe),
            "--repo", EDL_NG_REPO_URL,
            "--tag", EDL_NG_TAG,
            "--release-asset", asset_pattern,
            str(TOOLS_DIR)
        ]
        utils.run_command(fetch_command, capture=True)

        downloaded_zip_path = TOOLS_DIR / asset_pattern
        
        if not downloaded_zip_path.exists():
            raise FileNotFoundError(f"Failed to find the downloaded edl-ng zip archive: {asset_pattern}")
        
        with zipfile.ZipFile(downloaded_zip_path, 'r') as zip_ref:
            edl_info = None
            for member in zip_ref.infolist():
                if member.filename.endswith('edl-ng.exe'):
                    edl_info = member
                    break
            
            if not edl_info:
                raise FileNotFoundError("edl-ng.exe not found inside the downloaded zip archive.")

            zip_ref.extract(edl_info, path=TOOLS_DIR)
            
            extracted_path = TOOLS_DIR / edl_info.filename
            if extracted_path != edl_ng_exe:
                shutil.move(extracted_path, edl_ng_exe)
                parent_dir = extracted_path.parent
                if parent_dir.is_dir() and parent_dir != TOOLS_DIR:
                    try:
                        parent_dir.rmdir()
                    except OSError:
                        shutil.rmtree(parent_dir, ignore_errors=True)

        downloaded_zip_path.unlink()
        print("[+] edl-ng download and extraction successful.")
        return edl_ng_exe

    except (subprocess.CalledProcessError, FileNotFoundError, KeyError, IndexError) as e:
        print(f"[!] Error downloading or extracting edl-ng: {e}", file=sys.stderr)
        sys.exit(1)

def check_edl_device(silent=False):
    if not silent:
        print("[*] Checking for Qualcomm EDL (9008) device...")
    try:
        result = subprocess.run(
            ['wmic', 'path', 'Win32_PnPEntity', 'where', "Name like 'Qualcomm%9008%'", 'get', 'Name'],
            capture_output=True, text=True, encoding='utf-8', errors='ignore', shell=True
        )
        if "Qualcomm" in result.stdout and "9008" in result.stdout:
            if not silent:
                print("[+] Qualcomm EDL device found.")
            return True
        else:
            if not silent:
                print("[!] No Qualcomm EDL (9008) device found in Device Manager.")
                print("[!] Please connect your device in EDL mode.")
            return False
    except FileNotFoundError:
        if not silent:
            print("[!] WMIC command not found. Cannot check for EDL device.", file=sys.stderr)
        return False
    except Exception as e:
        if not silent:
            print(f"[!] Error checking for EDL device: {e}", file=sys.stderr)
        return False

def wait_for_edl():
    print("\n--- WAITING FOR EDL DEVICE ---")
    if check_edl_device():
        return
    
    while not check_edl_device(silent=True):
        print("[*] Waiting for Qualcomm EDL (9008) device... (Press Ctrl+C to cancel)")
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n[!] EDL wait cancelled by user.")
            raise
    print("[+] EDL device connected.")

def _run_edl_command(loader_path, args_list):
    edl_ng_exe = _ensure_edl_ng()
    base_cmd = [str(edl_ng_exe), "--loader", str(loader_path)]
    base_cmd.extend(args_list)
    return utils.run_command(base_cmd)

def edl_read_part(loader_path, partition, output_file):
    return _run_edl_command(loader_path, ["read-part", partition, str(output_file)])

def edl_write_part(loader_path, partition, input_file):
    return _run_edl_command(loader_path, ["write-part", partition, str(input_file)])

def edl_reset(loader_path, mode=None):
    cmd = ["reset"]
    if mode == "edl":
        cmd.append("edl")
    return _run_edl_command(loader_path, cmd)

def edl_rawprogram(loader_path, memory_type, raw_xmls, patch_xmls):
    cmd = [
        "--memory", memory_type, 
        "rawprogram", 
        *[str(p) for p in raw_xmls], 
        *[str(p) for p in patch_xmls]
    ]
    return _run_edl_command(loader_path, cmd)