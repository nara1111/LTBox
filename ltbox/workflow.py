import subprocess
import sys
import shutil
from typing import Optional, Dict

from ltbox.constants import *
from ltbox import utils, device, actions

def patch_all(wipe: int = 0, skip_adb: bool = False, lang: Optional[Dict[str, str]] = None) -> None:
    
    lang = lang or {}
    
    print(lang.get('wf_step1_clean', "--- [STEP 1/9] Cleaning up previous output folders ---"))
    output_folders_to_clean = [
        OUTPUT_DIR, 
        OUTPUT_ROOT_DIR, 
        OUTPUT_DP_DIR, 
        OUTPUT_ANTI_ROLLBACK_DIR,
        OUTPUT_XML_DIR
    ]
    
    for folder in output_folders_to_clean:
        if folder.exists():
            try:
                shutil.rmtree(folder)
                print(lang.get('wf_removed', "  > Removed: {name}").format(name=folder.name))
            except OSError as e:
                print(lang.get('wf_remove_error', "[!] Error removing {name}: {e}").format(name=folder.name, e=e), file=sys.stderr)

    if wipe == 1:
        print(lang.get('wf_wipe_mode_start', "\n--- [WIPE MODE] Starting Automated Install & Flash ROW Firmware Process ---"))
    else:
        print(lang.get('wf_nowipe_mode_start', "\n--- [NO WIPE MODE] Starting Automated Update & Flash ROW Firmware Process ---"))
    
    print("\n" + "="*61)
    print(lang.get('wf_step2_device_info', "  STEP 2/9: Waiting for ADB/Fastboot Connection & Getting Device Info"))
    print("="*61)
    
    dev = device.DeviceController(skip_adb=skip_adb)

    active_slot_suffix = actions.detect_active_slot_robust(dev, skip_adb)
    
    device_model: Optional[str] = None

    if not skip_adb:
        try:
            device_model = dev.get_device_model()
            if not device_model:
                raise SystemExit(lang.get('wf_err_adb_model', "CRITICAL ERROR: Failed to get device model via ADB. Aborting for safety."))
            else:
                print(lang.get('wf_device_model', "[+] Device Model: {model}").format(model=device_model))
        except Exception as e:
             raise SystemExit(lang.get('wf_err_get_model', "CRITICAL ERROR: Error getting device model: {e}").format(e=e))

    active_slot_str = active_slot_suffix if active_slot_suffix else lang.get('wf_active_slot_unknown', 'Unknown')
    print(lang.get('wf_active_slot', "[+] Active Slot: {slot}").format(slot=active_slot_str))
    print(lang.get('wf_step2_complete', "\n--- [STEP 2/9] Device Info Check FINISHED ---"))

    print(lang.get('wf_step3_wait_image', "\n--- [STEP 3/9] Waiting for RSA Firmware 'image' folder ---"))
    prompt = lang.get('wf_step3_prompt', 
        ("Please copy the entire 'image' folder from your\n"
        "         unpacked Lenovo RSA firmware into the main directory.\n"
        r"         (Typical Location: C:\ProgramData\RSA\Download\RomFiles\...)"
        )
    )
    utils.wait_for_directory(IMAGE_DIR, prompt, lang=lang)
    print(lang.get('wf_step3_found', "[+] 'image' folder found."))
    
    skip_dp_workflow = False
    
    try:
        print("\n" + "="*61)
        print(lang.get('wf_step4_convert', "  STEP 4/9: Converting Firmware (PRC to ROW) & Validating Model"))
        print("="*61)
        actions.convert_images(device_model=device_model, skip_adb=skip_adb)
        print(lang.get('wf_step4_complete', "\n--- [STEP 4/9] Firmware Conversion & Validation SUCCESS ---"))

        print("\n" + "="*61)
        print(lang.get('wf_step5_modify_xml', "  STEP 5/9: Modifying XML Files"))
        print("="*61)
        actions.modify_xml(wipe=wipe)
        print(lang.get('wf_step5_complete', "\n--- [STEP 5/9] XML Modification SUCCESS ---"))
        
        print("\n" + "="*61)
        print(lang.get('wf_step6_dump', "  STEP 6/9: Dumping devinfo/persist for patching (fh_loader)"))
        print("="*61)

        suffix = active_slot_suffix if active_slot_suffix else ""
        boot_target = f"boot{suffix}"
        vbmeta_target = f"vbmeta_system{suffix}"
        
        extra_dumps = [boot_target, vbmeta_target]
        
        print(lang.get('wf_step6_extra_dumps', "[*] Scheduled extra dumps for ARB check: {dumps}").format(dumps=', '.join(extra_dumps)))
        
        dump_status = actions.read_edl_fhloader(
            skip_adb=skip_adb, 
            skip_reset=False, 
            additional_targets=extra_dumps
        )

        if dump_status == "SKIP_DP":
            skip_dp_workflow = True
            print(lang.get('wf_skip_dp', "[!] Skipping devinfo/persist patching and flashing steps."))
        print(lang.get('wf_step6_complete', "\n--- [STEP 6/9] Dump SUCCESS ---"))
        
        
        if not skip_dp_workflow:
            print("\n" + "="*61)
            print(lang.get('wf_step7_patch_dp', "  STEP 7/9: Patching devinfo/persist"))
            print("="*61)
            actions.edit_devinfo_persist()
            print(lang.get('wf_step7_complete', "\n--- [STEP 7/9] Patching SUCCESS ---"))
        else:
            print("\n" + "="*61)
            print(lang.get('wf_step7_skipped', "  STEP 7/9: Patching devinfo/persist (SKIPPED)"))
            print("="*61)

        
        print("\n" + "="*61)
        print(lang.get('wf_step8_check_arb', "  STEP 8/9: Checking and Patching Anti-Rollback"))
        print("="*61)
        
        print(lang.get('wf_step8_use_dumps', "[*] Using Dumped Images for ARB Check..."))
        dumped_boot = BACKUP_DIR / f"{boot_target}.img"
        dumped_vbmeta = BACKUP_DIR / f"{vbmeta_target}.img"
        
        arb_status_result = actions.read_anti_rollback(
            dumped_boot_path=dumped_boot,
            dumped_vbmeta_path=dumped_vbmeta
        )
        
        if arb_status_result[0] == 'ERROR':
            print("\n" + "!"*61)
            print(lang.get('wf_step8_err_arb_check', "  CRITICAL ERROR: Anti-Rollback check failed!"))
            print(lang.get('wf_step8_err_arb_check_detail', "  Could not determine device security version."))
            print(lang.get('wf_step8_err_arb_abort', "  Aborting process to prevent bricking."))
            print("!"*61)
            sys.exit(1)

        actions.patch_anti_rollback(comparison_result=arb_status_result)
        print(lang.get('wf_step8_complete', "\n--- [STEP 8/9] Anti-Rollback Check/Patch SUCCESS ---"))
        
        print("\n" + "="*61)
        print(lang.get('wf_step9_flash', "  [FINAL STEP 9/9] Flashing All Images via EDL"))
        print("="*61)
        print(lang.get('wf_step9_flash_info', "The device will now be flashed with all modified images."))
        actions.flash_edl(skip_reset_edl=True, skip_dp=skip_dp_workflow) 
        
        print("\n" + "=" * 61)
        print(lang.get('wf_process_complete', "  FULL PROCESS COMPLETE!"))
        print(lang.get('wf_process_complete_info', "  Your device should now reboot with a patched ROW firmware."))
        print("=" * 61)

    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError, KeyError) as e:
        print("\n" + "!" * 61)
        print(lang.get('wf_err_halted', "  AN ERROR OCCURRED: Process Halted."))
        print(lang.get('wf_err_details', "  Error details: {e}").format(e=e))
        print("!" * 61)
        sys.exit(1)
    except SystemExit as e:
        print("\n" + "!" * 61)
        print(lang.get('wf_err_halted_script', "  PROCESS HALTED BY SCRIPT: {e}").format(e=e))
        print("!" * 61)
    except KeyboardInterrupt:
        print("\n" + "!" * 61)
        print(lang.get('wf_err_cancelled', "  PROCESS CANCELLED BY USER."))
        print("!" * 61)