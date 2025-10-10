import re
import sys
from pathlib import Path

def get_kernel_version(file_path):
    """
    Robustly extracts and prints the Linux kernel version in x.y.z format.
    It finds all printable character sequences in the binary to locate the version string.
    """
    kernel_file = Path(file_path)
    if not kernel_file.exists():
        sys.stderr.write(f"Error: Kernel file not found at '{file_path}'\n")
        sys.exit(1)

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
                        sys.stderr.write(f"Full kernel string found: {line.strip()}\n")
                        break
            except UnicodeDecodeError:
                continue

        if found_version:
            print(found_version)
        else:
            sys.stderr.write("Error: Could not find or parse 'Linux version' string in the kernel file.\n")
            sys.exit(1)

    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_kernel_version(sys.argv[1])
    else:
        get_kernel_version('kernel')