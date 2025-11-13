import os
import platform
import subprocess
import sys
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Generator, Any, Union, Dict, Tuple

from ltbox.constants import *
from .i18n import get_string

def run_command(
    command: Union[List[str], str], 
    shell: bool = False, 
    check: bool = True, 
    env: Optional[dict] = None, 
    capture: bool = False
) -> subprocess.CompletedProcess:
    env = env or os.environ.copy()
    env['PATH'] = str(TOOLS_DIR) + os.pathsep + str(DOWNLOAD_DIR) + os.pathsep + env['PATH']

    try:
        process = subprocess.run(
            command, shell=shell, check=check, capture_output=capture,
            text=True, encoding='utf-8', errors='ignore', env=env
        )

        if not capture:
            if process.stdout:
                print(process.stdout.strip())
            if process.stderr:
                print(process.stderr.strip(), file=sys.stderr)
        
        return process
    except FileNotFoundError as e:
        print(f"Error: Command not found - {e.filename}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(map(str, command)) if isinstance(command, list) else command}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"Stdout:\n{e.stdout.strip()}", file=sys.stderr)
        if e.stderr:
            print(f"Stderr:\n{e.stderr.strip()}", file=sys.stderr)
        raise

def get_platform_executable(name: str) -> Path:
    system = platform.system()
    executables = {
        "Windows": f"{name}.exe",
        "Linux": f"{name}-linux",
        "Darwin": f"{name}-macos"
    }
    exe_name = executables.get(system)
    if not exe_name:
        raise RuntimeError(f"Unsupported operating system: {system}")
    return DOWNLOAD_DIR / exe_name

def _wait_for_resource(
    target_path: Path, 
    check_func: Callable[[Path, Optional[List[str]]], bool], 
    prompt_msg: str, 
    item_list: Optional[List[str]] = None
) -> bool:
    target_path.mkdir(exist_ok=True, parents=True)
    while True:
        if check_func(target_path, item_list):
            return True
        
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')
            
        print(get_string('utils_wait_resource'))
        print(prompt_msg)
        if item_list:
            print(get_string('utils_missing_items'))
            for item in item_list:
                if not (target_path / item).exists():
                    print(f" - {item}")
        
        print(get_string('utils_press_enter'))
        try:
            input()
        except EOFError:
            sys.exit(1)

def wait_for_files(directory: Path, required_files: List[str], prompt_message: str) -> bool:
    return _wait_for_resource(
        directory, 
        lambda p, f: all((p / i).exists() for i in (f or [])), 
        prompt_message, 
        required_files
    )

def wait_for_directory(directory: Path, prompt_message: str) -> bool:
    return _wait_for_resource(
        directory, 
        lambda p, _: p.is_dir() and any(p.iterdir()), 
        prompt_message,
        None
    )

def check_dependencies() -> None:
    print(get_string('utils_check_deps'))
    dependencies = {
        "Python Environment": PYTHON_EXE,
        "ADB": ADB_EXE,
        "Fastboot": FASTBOOT_EXE,
        "RSA4096 Key": KEY_MAP["2597c218aae470a130f61162feaae70afd97f011"],
        "RSA2048 Key": KEY_MAP["cdbb77177f731920bbe0a0f94f84d9038ae0617d"],
        "avbtool": AVBTOOL_PY,
        "fetch tool": get_platform_executable("fetch")
    }
    missing_deps = [name for name, path in dependencies.items() if not Path(path).exists()]

    if missing_deps:
        for name in missing_deps:
            print(get_string('utils_missing_dep').format(name=name))
        print(get_string('utils_run_install'))
        sys.exit(1)

    print(get_string('utils_deps_found'))

def require_dependencies(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        check_dependencies() 
        return func(*args, **kwargs)
    return wrapper

@contextmanager
def working_directory(path: Path) -> Generator[None, None, None]:
    origin = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)

@contextmanager
def temporary_workspace(path: Path) -> Generator[Path, None, None]:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        if path.exists():
            try:
                shutil.rmtree(path)
            except OSError as e:
                print(f"Warning: Failed to clean up temporary workspace {path}: {e}", file=sys.stderr)

def show_image_info(files: List[str]) -> None:
    all_files: List[Path] = []
    for f in files:
        path = Path(f)
        if path.is_dir():
            all_files.extend(path.rglob('*.img'))
        elif path.is_file():
            all_files.append(path)

    if not all_files:
        print(get_string('scan_no_files'))
        return
        
    output_lines = [
        "\n" + "=" * 42,
        get_string('utils_processing_images'),
        "=" * 42 + "\n"
    ]
    print("\n".join(output_lines))

    for file_path in sorted(all_files):
        info_header = get_string('utils_processing_file').format(file_path=file_path) 
        print(info_header)
        output_lines.append(info_header)

        if not file_path.exists():
            not_found_msg = get_string('utils_file_not_found').format(file_path=file_path)
            print(not_found_msg)
            output_lines.append(not_found_msg)
            continue

        try:
            process = run_command(
                [str(PYTHON_EXE), str(AVBTOOL_PY), "info_image", "--image", str(file_path)],
                capture=True
            )
            output_text = process.stdout.strip()
            print(output_text)
            output_lines.append(output_text)
        except (subprocess.CalledProcessError) as e:
            error_message = get_string('scan_failed').format(filename=file_path.name, e="")
            print(error_message, file=sys.stderr)
            if e.stderr:
                print(e.stderr.strip(), file=sys.stderr)
            output_lines.append(error_message)
        finally:
            output_lines.append("---------------------------------\n")

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_filename = BASE_DIR / f"image_info_{timestamp}.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(get_string('scan_saved_to').format(filename=output_filename))
    except IOError as e:
        print(get_string('utils_save_error').format(e=e), file=sys.stderr)

def clean_workspace() -> None:
    print(get_string('utils_cleaning_title'))
    print(get_string('utils_cleaning_warning'))
    print("-" * 50)

    folders_to_remove = [
        INPUT_CURRENT_DIR, INPUT_NEW_DIR,
        OUTPUT_DIR, OUTPUT_ROOT_DIR, OUTPUT_DP_DIR, OUTPUT_ANTI_ROLLBACK_DIR,
        WORK_DIR,
        IMAGE_DIR,
        WORKING_DIR,
        OUTPUT_XML_DIR,
    ]
    
    print(get_string('utils_removing_dirs'))
    for folder in folders_to_remove:
        if folder.exists():
            try:
                shutil.rmtree(folder)
                print(get_string('utils_removed').format(name=f"{folder.name}{os.sep}"))
            except OSError as e:
                print(get_string('utils_remove_error').format(name=folder.name, e=e), file=sys.stderr)
        else:
            print(get_string('utils_skipping').format(name=f"{folder.name}{os.sep}"))

    print(get_string('utils_cleaning_dl'))
    dl_files_to_remove = [
        "*.zip",
        "*.tar.gz",
    ]
    
    cleaned_dl_files = 0
    for pattern in dl_files_to_remove:
        for f in DOWNLOAD_DIR.glob(pattern):
            try:
                f.unlink()
                print(get_string('utils_removed_temp').format(name=f.name))
                cleaned_dl_files += 1
            except OSError as e:
                print(get_string('utils_remove_error').format(name=f.name, e=e), file=sys.stderr)

    if cleaned_dl_files == 0:
        print(get_string('utils_no_temp_dl'))


    print(get_string('utils_cleaning_root'))
    file_patterns_to_remove = [
        "*.bak.img",
        "*.root.img",
        "*prc.img",
        "*modified.img",
        "image_info_*.txt",
        "KernelSU*.apk",
        "devinfo.img", 
        "persist.img", 
        "boot.img", 
        "vbmeta.img",
        "platform-tools.zip"
    ]
    
    cleaned_root_files = 0
    for pattern in file_patterns_to_remove:
        for f in BASE_DIR.glob(pattern):
            try:
                f.unlink()
                print(get_string('utils_removed').format(name=f.name))
                cleaned_root_files += 1
            except OSError as e:
                print(get_string('utils_remove_error').format(name=f.name, e=e), file=sys.stderr)
    
    if cleaned_root_files == 0:
        print(get_string('utils_no_temp_root'))

    print(get_string('utils_clean_complete'))

def _process_binary_file(
    input_path: Union[str, Path], 
    output_path: Union[str, Path], 
    patch_func: Any, 
    copy_if_unchanged: bool = True,
    **kwargs: Any
) -> bool:
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        print(get_string("img_proc_err_not_found").format(path=input_path), file=sys.stderr)
        return False

    try:
        content = input_path.read_bytes()
        modified_content, stats = patch_func(content, **kwargs)

        if stats.get('changed', False):
            output_path.write_bytes(modified_content)
            print(get_string("img_proc_success").format(msg=stats.get('message', 'Modifications applied.')))
            print(get_string("img_proc_saved").format(name=output_path.name))
            return True
        else:
            print(get_string("img_proc_no_change").format(name=input_path.name, msg=stats.get('message', 'No patterns found')))
            if copy_if_unchanged:
                print(get_string("img_proc_copying").format(name=output_path.name))
                if input_path != output_path:
                    shutil.copy(input_path, output_path)
                return True
            return False

    except Exception as e:
        print(get_string("img_proc_error").format(name=input_path.name, e=e), file=sys.stderr)
        return False