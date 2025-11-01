# LTBox

## ⚠️ Important: Disclaimer

**This project is for educational purposes ONLY.**

Modifying your device's boot images carries significant risks, including but not limited to, bricking your device, data loss, or voiding your warranty. The author **assumes no liability** and is not responsible for any **damage or consequence** that may occur to **your device or anyone else's device** from using these scripts.

**You are solely responsible for any consequences. Use at your own absolute risk.**

---

## 1. Core Vulnerability & Overview

This toolkit exploits a security vulnerability found in certain Lenovo Android tablets. These devices have firmware signed with publicly available **AOSP (Android Open Source Project) test keys**.

Because of this vulnerability, the device's bootloader trusts and boots any image signed with these common test keys, even if the bootloader is **locked**.

This toolkit is an all-in-one collection of scripts that leverages this flaw to perform advanced modifications on a device with a locked bootloader.

### Target Models

* Lenovo Legion Y700 (2nd, 3rd, 4th Gen)
* Lenovo Tab Plus AI (AKA Yoga Pad Pro AI)
* Lenovo Xiaoxin Pad Pro GT

*...Other recent Lenovo devices (released in 2024 or later with Qualcomm chipsets) may also be vulnerable.*

## 2. Toolkit Purpose & Features

This toolkit provides an all-in-one solution for the following tasks **without unlocking the bootloader**:

1.  **Region Conversion (PRC → ROW)**
    * Converts the region code in `vendor_boot.img` to allow flashing a global (ROW) ROM on a Chinese (PRC) model.
    * Re-signs the `vbmeta.img` with the AOSP test keys to validate the modified `vendor_boot`.
2.  **Rooting**
    * Patches the stock `boot.img` by replacing the original kernel with [one that includes KernelSU](https://github.com/WildKernels/GKI_KernelSU_SUSFS).
    * Re-signs the patched `boot.img` with AOSP test keys.
3.  **Region Code Reset**
    * Modifies byte patterns in `devinfo.img` and `persist.img` to reset region-lock settings.
4.  **EDL Partition Dump/Write**
    * Dumps the `devinfo` and `persist` partitions directly from the device in EDL mode.
    * Flashes the patched `devinfo.img` and `persist.img` back to the device in EDL mode.
5.  **Anti-Rollback (ARB) Bypass**
    * Patches firmware images (e.g., `boot.img`, `vbmeta_system.img`) that you intend to flash (e.g., for a downgrade).
    * It reads the rollback index from your *currently installed* firmware and forcibly applies that same (higher) index to the *new* firmware, bypassing Anti-Rollback Protection.

## 3. Prerequisites

Before you begin, place the required firmware images into the correct `input*` folders. The script will guide you if files are missing.

* **For `Convert ROM` (Menu 1):**
    * Place `vendor_boot.img` and `vbmeta.img` in the `input` folder.

* **For `Create Rooted boot.img` (Menu 5):**
    * Place `boot.img` in the `input_root` folder.

* **For `EDL Dump/Patch/Write` (Menu 2, 3, 4) AND `Bypass Anti-Rollback` (Menu 6):**
    * Place the EDL loader file (`xbl_s_devprg_ns.melf`) in the `input_dp` folder.
    * For **Patch (Menu 3)**, you must first place `devinfo.img` and/or `persist.img` in the `input_dp` folder. (You can use **Menu 2** to dump them there).

* **For `Bypass Anti-Rollback` (Menu 6):**
    * **Step 1 (Auto-Dump):** The script will first ask for the EDL loader file (in `input_dp`) and **automatically dump your device's current** `boot.img` and `vbmeta_system.img` into the `input_current` folder.
    * **Step 2 (User-Input):** After the dump is complete, the script will pause and ask you to place the **new (downgrade)** `boot.img` and `vbmeta_system.img` into the `input_new` folder.

## 4. How to Use

1.  **Place Images:** Put the necessary `.img` files (and loader file, if needed) into the correct folder as described in **Section 3**.
2.  **Run the Script:** Double-click `start.bat`.
3.  **Select Task:** Choose an option from the menu. The script will wait for you to place the required files if they are not found.
4.  **Get Results:** After a script finishes, the modified images will be saved in a corresponding `output*` folder (e.g., `output`, `output_root`, `output_dp`).
5.  **Flash the Images:** Flash the new `.img` file(s) from the output folder to your device using `fastboot` or an EDL tool.

## 5. Script Descriptions

* **`start.bat`**: This is the main script you will run. It provides a menu to access all major functions.
    * **Menu 1. Convert ROM (PRC to ROW):** Reads from `input`, saves to `output`.
    * **Menu 2. Dump devinfo/persist via EDL:** Dumps partitions directly into the `input_dp` folder.
    * **Menu 3. Patch devinfo/persist (Region Code Reset):** Reads from `input_dp`, saves to `output_dp`.
    * **Menu 4. Write devinfo/persist via EDL (Flash patched):** Reads patched images from `output_dp` and flashes them.
    * **Menu 5. Create Rooted boot.img:** Reads from `input_root`, saves to `output_root`.
    * **Menu 6. Bypass Anti-Rollback:** **Dumps current firmware (`boot`/`vbmeta_system`) via EDL to `input_current`**, then reads new firmware from `input_new`, and saves patched images to `output_anti_rollback`.
    * **Menu 7. Clean Workspace:** Deletes all `input*` and `output*` folders, temporary files, and downloaded tools (like `fetch.exe`, `edl-ng.exe`, `avb/`). **Keeps `python3` and `backup` folders.**
    * **Menu 8. Exit:** Closes the script.

* **`info_image.bat`**: A separate utility script. Drag & drop `.img` file(s) or folder(s) onto this script to see AVB (Android Verified Boot) information.
    * *Output: `image_info_*.txt`*