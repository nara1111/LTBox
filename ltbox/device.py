import platform
import subprocess
import sys
import time
import zipfile
import shutil
import serial.tools.list_ports

from ltbox.constants import *
from ltbox import utils

# --- ADB Device Handling ---
def wait_for_adb():
    print("\n--- WAITING FOR ADB DEVICE ---")
    print("[!] Please enable USB Debugging on your device, connect it via USB.")
    print("[!] A 'Allow USB debugging?' prompt will appear on your device.")
    print("[!] Please check 'Always allow from this computer' and tap 'OK'.")
    try:
        utils.run_command([str(ADB_EXE), "wait-for-device"])
        print("[+] ADB device connected.")
    except Exception as e:
        print(f"[!] Error waiting for ADB device: {e}", file=sys.stderr)
        raise

def get_device_model():
    print("[*] Getting device model via ADB...")
    try:
        result = utils.run_command([str(ADB_EXE), "shell", "getprop", "ro.product.model"], capture=True)
        model = result.stdout.strip()
        if not model:
            print("[!] Could not get device model. Is the device authorized?")
            return None
        print(f"[+] Found device model: {model}")
        return model
    except Exception as e:
        print(f"[!] Error getting device model: {e}", file=sys.stderr)
        print("[!] Please ensure the device is connected and authorized.")
        return None

def reboot_to_edl():
    print("[*] Attempting to reboot device to EDL mode via ADB...")
    try:
        utils.run_command([str(ADB_EXE), "reboot", "edl"])
        print("[+] Reboot command sent. Please wait for the device to enter EDL mode.")
    except Exception as e:
        print(f"[!] Failed to send reboot command: {e}", file=sys.stderr)
        print("[!] Please reboot to EDL manually if it fails.")

# --- EDL Device Handling ---
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
        ports = serial.tools.list_ports.comports()
        for port in ports:
            is_qualcomm_port = (port.description and "Qualcomm" in port.description and "9008" in port.description) or \
                               (port.hwid and "VID:PID=05C6:9008" in port.hwid.upper())
            
            if is_qualcomm_port:
                if not silent:
                    print(f"[+] Qualcomm EDL device found: {port.device}")
                return True
        
        if not silent:
            print("[!] No Qualcomm EDL (9008) device found.")
            print("[!] Please connect your device in EDL mode.")
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