import subprocess
from typing import Optional, Dict

from .. import constants as const
from .. import utils, device
from ..i18n import get_string

def detect_active_slot_robust(dev: device.DeviceController) -> Optional[str]:
    active_slot = None

    if not dev.skip_adb:
        try:
            active_slot = dev.get_active_slot_suffix()
        except Exception:
            pass

    if not active_slot:
        print(get_string("act_slot_adb_fail"))
        
        if not dev.skip_adb:
            print(get_string("act_reboot_bootloader"))
            try:
                dev.reboot_to_bootloader()
            except Exception as e:
                print(get_string("act_err_reboot_bl").format(e=e))
        else:
            print("\n" + "="*60)
            print(get_string("act_manual_fastboot"))
            print("="*60 + "\n")

        dev.wait_for_fastboot()
        active_slot = dev.get_active_slot_suffix_from_fastboot()

        if not dev.skip_adb:
            print(get_string("act_slot_detected_sys"))
            dev.fastboot_reboot_system()
            print(get_string("act_wait_adb"))
            dev.wait_for_adb()
        else:
            print("\n" + "="*60)
            print(get_string("act_detect_complete"))
            print(get_string("act_manual_edl"))
            print("="*60 + "\n")

    return active_slot

def disable_ota(dev: device.DeviceController) -> None:
    if dev.skip_adb:
        print(get_string("act_ota_skip_adb"))
        return
    
    print(get_string("act_start_ota"))
    
    print("\n" + "="*61)
    print(get_string("act_ota_step1"))
    print("="*61)
    try:
        dev.wait_for_adb()
        print(get_string("act_adb_ok"))
    except Exception as e:
        print(get_string("act_err_wait_adb").format(e=e), file=sys.stderr)
        raise

    print("\n" + "="*61)
    print(get_string("act_ota_step2"))
    print("="*61)
    
    command = [
        str(const.ADB_EXE), 
        "shell", "pm", "disable-user", "--user", "0", "com.lenovo.ota"
    ]
    
    print(get_string("act_run_cmd").format(cmd=' '.join(command)))
    try:
        result = utils.run_command(command, capture=True)
        if "disabled" in result.stdout.lower() or "already disabled" in result.stdout.lower():
            print(get_string("act_ota_disabled"))
            print(result.stdout.strip())
        else:
            print(get_string("act_ota_unexpected"))
            print(f"Stdout: {result.stdout.strip()}")
            if result.stderr:
                print(f"Stderr: {result.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(get_string("act_err_ota_cmd").format(e=e), file=sys.stderr)
        raise

    print(get_string("act_ota_finished"))