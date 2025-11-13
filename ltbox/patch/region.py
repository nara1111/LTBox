import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, Union

from ..constants import *
from .. import utils
from ..i18n import get_string

def _patch_vendor_boot_logic(content: bytes, **kwargs: Any) -> Tuple[bytes, Dict[str, Any]]:
    patterns_row = {
        b"\x2E\x52\x4F\x57": b"\x2E\x50\x52\x43",
        b"\x49\x52\x4F\x57": b"\x49\x50\x52\x43"
    }
    patterns_prc = [b"\x2E\x50\x52\x43", b"\x49\x50\x52\x43"]
    
    modified_content = content
    found_row_count = 0

    for target, replacement in patterns_row.items():
        count = content.count(target)
        if count > 0:
            print(get_string("img_vb_found_replace").format(pattern=target.hex().upper(), count=count))
            modified_content = modified_content.replace(target, replacement)
            found_row_count += count

    if found_row_count > 0:
        return modified_content, {'changed': True, 'message': get_string("img_vb_replaced_total").format(count=found_row_count)}
    
    found_prc = any(content.count(target) > 0 for target in patterns_prc)
    if found_prc:
        return content, {'changed': False, 'message': get_string("img_vb_already_prc")}
    
    return content, {'changed': False, 'message': get_string("img_vb_no_patterns")}

def edit_vendor_boot(input_file_path: str) -> None:
    input_file = Path(input_file_path)
    output_file = input_file.parent / "vendor_boot_prc.img"
    
    if not utils._process_binary_file(input_file, output_file, _patch_vendor_boot_logic, copy_if_unchanged=True):
        sys.exit(1)

def check_target_exists(target_code: str) -> bool:
    target_bytes = f"{target_code.upper()}XX".encode('ascii')
    files_to_check = [BASE_DIR / "devinfo.img", BASE_DIR / "persist.img"]
    found = False
    
    for f in files_to_check:
        if not f.exists():
            continue
        try:
            content = f.read_bytes()
            if content.count(target_bytes) > 0:
                found = True
                break
        except Exception as e:
            print(get_string("img_chk_err_read").format(name=f.name, e=e), file=sys.stderr)
    return found

def detect_region_codes() -> Dict[str, Optional[str]]:
    results: Dict[str, Optional[str]] = {}
    files_to_check = ["devinfo.img", "persist.img"]

    if not COUNTRY_CODES:
        print(get_string("img_det_warn_empty"), file=sys.stderr)
        return {f: None for f in files_to_check}

    for filename in files_to_check:
        file_path = BASE_DIR / filename
        results[filename] = None
        
        if not file_path.exists():
            continue
            
        try:
            content = file_path.read_bytes()
            for code, _ in COUNTRY_CODES.items():
                target_bytes = b'\x00\x00\x00' + f"{code.upper()}".encode('ascii') + b'XX\x00\x00\x00'
                if target_bytes in content:
                    results[filename] = code
                    break
        except Exception as e:
            print(get_string("img_det_err_read").format(name=filename, e=e), file=sys.stderr)
            
    return results

def _patch_region_code_logic(content: bytes, **kwargs: Any) -> Tuple[bytes, Dict[str, Any]]:
    current_code = kwargs.get('current_code')
    replacement_code = kwargs.get('replacement_code')
    
    if not current_code or not replacement_code:
        return content, {'changed': False, 'message': get_string("img_code_invalid")}

    target_string = f"000000{current_code.upper()}XX000000"
    target_bytes = b'\x00\x00\x00' + f"{current_code.upper()}".encode('ascii') + b'XX\x00\x00\x00'
    
    replacement_string = f"000000{replacement_code.upper()}XX000000"
    replacement_bytes = b'\x00\x00\x00' + f"{replacement_code.upper()}".encode('ascii') + b'XX\x00\x00\x00'

    if target_bytes == replacement_bytes:
        return content, {'changed': False, 'message': get_string("img_code_already").format(code=replacement_code.upper())}

    count = content.count(target_bytes)
    if count > 0:
        print(get_string("img_code_replace").format(target=target_string, count=count, replacement=replacement_string))
        modified_content = content.replace(target_bytes, replacement_bytes)
        return modified_content, {'changed': True, 'message': get_string("img_code_replaced_total").format(count=count), 'count': count}
    
    return content, {'changed': False, 'message': get_string("img_code_not_found").format(target=target_string)}

def patch_region_codes(replacement_code: str, target_map: Dict[str, Optional[str]]) -> int:
    if not replacement_code or len(replacement_code) != 2:
        print(get_string("img_patch_code_err").format(code=replacement_code), file=sys.stderr)
        sys.exit(1)
        
    total_patched = 0
    files_to_output = {
        "devinfo.img": "devinfo_modified.img",
        "persist.img": "persist_modified.img"
    }

    print(get_string("img_patch_start").format(code=replacement_code))

    for filename, current_code in target_map.items():
        if filename not in files_to_output:
            continue
            
        input_file = BASE_DIR / filename
        output_file = BASE_DIR / files_to_output[filename]
        
        if not input_file.exists():
            continue
            
        print(get_string("img_patch_processing").format(name=input_file.name))
        
        if not current_code:
            print(get_string("img_patch_skip").format(name=filename))
            continue

        success = utils._process_binary_file(
            input_file, 
            output_file, 
            _patch_region_code_logic, 
            copy_if_unchanged=True,
            current_code=current_code, 
            replacement_code=replacement_code
        )
        
        if success:
             pass

    print(get_string("img_patch_finish"))
    return total_patched