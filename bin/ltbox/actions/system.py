from typing import Optional

from .. import device, utils
from ..errors import ToolError
from ..i18n import get_string


def detect_active_slot_robust(dev: device.DeviceController) -> Optional[str]:
    try:
        return dev.detect_active_slot()
    except Exception as e:
        raise ToolError(get_string("act_warn_slot_fail")) from e


def disable_ota(dev: device.DeviceController) -> None:

    utils.ui.echo(get_string("act_start_ota"))

    dev.adb.wait_for_device()

    utils.ui.echo(get_string("act_ota_settings_put"))
    try:
        dev.adb.shell("settings put global ota_disable_automatic_update 1")
        dev.adb.shell("settings put secure lenovo_ota_new_version_found 0")
    except Exception as e:
        utils.ui.echo(f"Warning: Failed to update settings: {e}", err=True)

    packages = ["com.lenovo.ota", "com.tblenovo.lenovowhatsnew", "com.lenovo.tbengine"]
    _disable_ota_packages(dev, packages)

    utils.ui.echo(get_string("act_ota_factory_reset_notice"))
    utils.ui.echo(get_string("act_ota_finished"))


def _disable_ota_packages(
    dev: device.DeviceController,
    packages: list[str],
) -> None:
    for pkg in packages:
        _clear_package_data(dev, pkg)
        utils.ui.echo(get_string("act_ota_uninstalling").format(pkg=pkg))
        _uninstall_package(dev, pkg)


def _clear_package_data(dev: device.DeviceController, package: str) -> None:
    try:
        dev.adb.shell(f"pm clear {package}")
    except Exception:
        return


def _uninstall_package(dev: device.DeviceController, package: str) -> None:
    try:
        output = dev.adb.shell(f"pm uninstall -k --user 0 {package}")
        if "Success" in output:
            utils.ui.echo(get_string("act_ota_uninstall_success").format(pkg=package))
        else:
            utils.ui.echo(get_string("act_ota_uninstall_fail").format(pkg=package))
    except Exception:
        utils.ui.echo(get_string("act_ota_uninstall_fail").format(pkg=package))
