import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Tuple

from . import actions
from . import constants as const
from . import device, utils
from .context import TaskContext
from .errors import DeviceError, LTBoxError, UserCancelError
from .i18n import get_string
from .logger import logging_context


@dataclass
class WorkflowState:
    skip_dp_workflow: bool = False
    boot_target: Optional[str] = None
    vbmeta_target: Optional[str] = None
    backup_dir_name: Optional[str] = None


def _cleanup_previous_outputs(ctx: TaskContext) -> None:
    output_folders_to_clean = [
        const.OUTPUT_DIR,
        const.OUTPUT_ROOT_DIR,
        const.OUTPUT_DP_DIR,
        const.OUTPUT_ANTI_ROLLBACK_DIR,
        const.OUTPUT_XML_DIR,
    ]

    for folder in output_folders_to_clean:
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except OSError as e:
                raise LTBoxError(
                    get_string("utils_remove_error").format(name=folder.name, e=e), e
                )


def _populate_device_info(ctx: TaskContext) -> None:
    ctx.active_slot_suffix = ctx.dev.detect_active_slot()

    if not ctx.dev.skip_adb:
        try:
            ctx.device_model = ctx.dev.adb.get_model()
            if not ctx.device_model:
                raise DeviceError(get_string("wf_err_adb_model"))
        except Exception as e:
            raise DeviceError(get_string("wf_err_get_model").format(e=e), e)


def _wait_for_input_images(ctx: TaskContext) -> None:
    prompt = get_string("act_prompt_image")
    utils.wait_for_directory(const.IMAGE_DIR, prompt)


def _convert_region_images(ctx: TaskContext) -> None:
    actions.convert_region_images(
        dev=ctx.dev,
        device_model=ctx.device_model,
        target_region=ctx.target_region,
        on_log=ctx.on_log,
    )


def _decrypt_and_modify_xml(ctx: TaskContext) -> None:
    actions.decrypt_x_files()
    actions.modify_xml(wipe=ctx.wipe)


def _dump_images(ctx: TaskContext) -> Tuple[bool, str, str]:
    skip_dp_workflow = ctx.wipe == 0

    suffix = ctx.active_slot_suffix if ctx.active_slot_suffix else ""
    boot_target = f"boot{suffix}"
    vbmeta_target = f"vbmeta_system{suffix}"
    extra_dumps = []
    if not ctx.skip_rollback:
        extra_dumps = [boot_target, vbmeta_target]

    if (not skip_dp_workflow) or extra_dumps:
        actions.dump_partitions(
            dev=ctx.dev,
            skip_reset=False,
            additional_targets=extra_dumps,
            default_targets=not skip_dp_workflow,
        )

    return skip_dp_workflow, boot_target, vbmeta_target


def _patch_devinfo(ctx: TaskContext, skip_dp_workflow: bool) -> Optional[str]:
    if not skip_dp_workflow:
        return actions.edit_devinfo_persist(
            on_log=ctx.on_log,
            on_confirm=lambda msg: utils.ui.prompt(msg + " (y/n) ").lower().strip()
            == "y",
        )
    return None


def _check_and_patch_arb(boot_target: str, vbmeta_target: str) -> None:
    if not boot_target or not vbmeta_target:
        raise LTBoxError(get_string("wf_err_halted"))

    dumped_boot = const.BACKUP_DIR / f"{boot_target}.img"
    dumped_vbmeta = const.BACKUP_DIR / f"{vbmeta_target}.img"

    arb_status_result = actions.read_anti_rollback(
        dumped_boot_path=dumped_boot, dumped_vbmeta_path=dumped_vbmeta
    )

    if arb_status_result[0] == "ERROR":
        raise LTBoxError(get_string("wf_step8_err_arb_abort"))

    actions.patch_anti_rollback(comparison_result=arb_status_result)


def _flash_images(ctx: TaskContext, skip_dp_workflow: bool) -> None:
    actions.flash_full_firmware(
        dev=ctx.dev, skip_reset_edl=True, skip_dp=skip_dp_workflow
    )


def _log_workflow_halt() -> None:
    utils.ui.echo(get_string("wf_err_halted"), err=True)


@dataclass(frozen=True)
class WorkflowStep:
    label_key: Optional[str]
    action: Callable[[], None]
    after_label_key: Optional[str] = None


def _run_step(ctx: TaskContext, step: WorkflowStep) -> None:
    if step.label_key:
        ctx.on_log(get_string(step.label_key))
    step.action()
    if step.after_label_key:
        ctx.on_log(get_string(step.after_label_key))


def _run_steps(ctx: TaskContext, steps: list[WorkflowStep]) -> None:
    for step in steps:
        _run_step(ctx, step)


def _run_dump_step(ctx: TaskContext, state: WorkflowState) -> None:
    skip_dp_workflow, boot_target, vbmeta_target = _dump_images(ctx)
    state.skip_dp_workflow = skip_dp_workflow
    state.boot_target = boot_target
    state.vbmeta_target = vbmeta_target


def _run_patch_dp_step(ctx: TaskContext, state: WorkflowState) -> None:
    if state.skip_dp_workflow:
        ctx.on_log(get_string("wf_step7_skipped"))
        return

    ctx.on_log(get_string("wf_step7_patch_dp"))
    state.backup_dir_name = _patch_devinfo(ctx, state.skip_dp_workflow)


def _run_arb_step(ctx: TaskContext, state: WorkflowState) -> None:
    if ctx.skip_rollback:
        ctx.on_log(get_string("wf_step8_skipped"))
        return

    ctx.on_log(get_string("wf_step8_check_arb"))
    if state.boot_target is None or state.vbmeta_target is None:
        raise LTBoxError(get_string("wf_err_halted"))
    _check_and_patch_arb(state.boot_target, state.vbmeta_target)


def _build_steps(ctx: TaskContext, state: WorkflowState) -> list[WorkflowStep]:
    return [
        WorkflowStep("wf_step1_clean", lambda: _cleanup_previous_outputs(ctx)),
        WorkflowStep("wf_step2_device_info", lambda: _populate_device_info(ctx)),
        WorkflowStep(None, lambda: _log_active_slot(ctx)),
        WorkflowStep(
            "wf_step3_wait_image",
            lambda: _wait_for_input_images(ctx),
            after_label_key="wf_step3_found",
        ),
        WorkflowStep("wf_step4_convert", lambda: _convert_region_images(ctx)),
        WorkflowStep("wf_step5_modify_xml", lambda: _decrypt_and_modify_xml(ctx)),
        WorkflowStep("wf_step6_dump", lambda: _run_dump_step(ctx, state)),
        WorkflowStep(None, lambda: _run_patch_dp_step(ctx, state)),
        WorkflowStep(None, lambda: _run_arb_step(ctx, state)),
        WorkflowStep(
            "wf_step9_flash", lambda: _flash_images(ctx, state.skip_dp_workflow)
        ),
    ]


def _log_active_slot(ctx: TaskContext) -> None:
    active_slot_str = (
        ctx.active_slot_suffix
        if ctx.active_slot_suffix
        else get_string("wf_active_slot_unknown")
    )
    ctx.on_log(get_string("act_active_slot").format(slot=active_slot_str))


def patch_all(
    dev: device.DeviceController,
    wipe: int = 0,
    skip_rollback: bool = False,
    target_region: str = "PRC",
) -> str:
    ctx = TaskContext(
        dev=dev,
        wipe=wipe,
        skip_rollback=skip_rollback,
        target_region=target_region,
        on_log=lambda s: utils.ui.info(s),
    )
    state = WorkflowState()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"log_{timestamp}.txt"
    command_name = "patch_all_wipe" if wipe == 1 else "patch_all"

    utils.ui.info(get_string("logging_enabled").format(log_file=log_file))
    utils.ui.info(get_string("logging_command").format(command=command_name))

    if target_region == "ROW":
        utils.ui.info(get_string("menu_main_install_keep_row"))
    else:
        utils.ui.info(get_string("menu_main_install_keep_prc"))

    try:
        with logging_context(log_file):
            if ctx.wipe == 1:
                ctx.on_log(get_string("wf_wipe_mode_start"))
            else:
                ctx.on_log(get_string("wf_nowipe_mode_start"))
            _run_steps(ctx, _build_steps(ctx, state))

            success_msg = get_string("wf_process_complete")
            success_msg += f"\n{get_string('wf_process_complete_info')}"

            if state.backup_dir_name:
                success_msg += f"\n\n{get_string('wf_backup_notice').format(dir=state.backup_dir_name)}"

            success_msg += f"\n\n{get_string('wf_notice_widevine')}"
            return success_msg

    except BaseException as e:
        _log_workflow_halt()
        if isinstance(e, KeyboardInterrupt):
            raise UserCancelError(get_string("act_op_cancel")) from e
        if isinstance(e, SystemExit):
            raise LTBoxError(get_string("wf_err_halted_script").format(e=e), e) from e
        if isinstance(
            e,
            (
                LTBoxError,
                subprocess.CalledProcessError,
                FileNotFoundError,
                RuntimeError,
                KeyError,
            ),
        ):
            raise
        raise
    finally:
        utils.ui.info(get_string("logging_finished").format(log_file=log_file))
