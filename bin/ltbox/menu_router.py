import sys
import webbrowser
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import i18n, menu_data
from .i18n import get_string
from .menu import TerminalMenu, select_menu_action
from .utils import ui
from .main import run_task, _read_current_version, _get_latest_version, SETTINGS_STORE


def _handle_menu_navigation(action: Optional[str]) -> Optional[str]:
    if action in ("back", "return", "exit"):
        return action
    return None


def _run_task_menu(
    dev: Any,
    registry: Any,
    menu_items: List[Any],
    title_key: str,
    breadcrumbs: Optional[str] = None,
    extra_kwargs_factory: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Optional[str]:
    action = select_menu_action(menu_items, title_key, breadcrumbs=breadcrumbs)
    navigation = _handle_menu_navigation(action)
    if navigation:
        return navigation

    if action:
        extras: Dict[str, Any] = {}
        if extra_kwargs_factory:
            extras = extra_kwargs_factory(action)
        run_task(action, dev, registry, extra_kwargs=extras)
    return None


def advanced_menu(dev: Any, registry: Any, target_region: str):
    main_title = get_string("menu_main_title")
    while True:
        menu_items = menu_data.get_advanced_menu_data(target_region)

        def _extra_kwargs(action: str) -> Dict[str, Any]:
            if action == "convert":
                return {"target_region": target_region}
            return {}

        action = _run_task_menu(
            dev,
            registry,
            menu_items,
            "menu_adv_title",
            breadcrumbs=main_title,
            extra_kwargs_factory=_extra_kwargs,
        )
        if action in ("back", "return"):
            return
        if action == "exit":
            sys.exit()


def _root_action_menu(
    dev: Any, registry: Any, gki: bool, root_type: str, breadcrumbs: str
):
    while True:
        menu_items = menu_data.get_root_menu_data(gki)

        def _extra_kwargs(action: str) -> Dict[str, Any]:
            if not gki:
                return {"root_type": root_type}
            return {}

        action = _run_task_menu(
            dev,
            registry,
            menu_items,
            "menu_root_title",
            breadcrumbs=breadcrumbs,
            extra_kwargs_factory=_extra_kwargs,
        )
        if action == "back":
            return
        if action == "return":
            return "main"
        if action == "exit":
            sys.exit()


def _select_root_mode_action(breadcrumbs: str) -> Optional[str]:
    menu_items = menu_data.get_root_mode_menu_data()
    return select_menu_action(
        menu_items, "menu_root_mode_title", breadcrumbs=breadcrumbs
    )


def _handle_ksu_mode(dev: Any, registry: Any, type_breadcrumbs: str) -> Optional[str]:
    mode_breadcrumbs = f"{type_breadcrumbs} > {get_string('menu_root_mode_title')}"
    dispatch_map = {
        "lkm": lambda: _root_action_menu(
            dev, registry, gki=False, root_type="ksu", breadcrumbs=mode_breadcrumbs
        ),
        "gki": lambda: _root_action_menu(
            dev, registry, gki=True, root_type="ksu", breadcrumbs=mode_breadcrumbs
        ),
    }

    while True:
        mode_action = _select_root_mode_action(breadcrumbs=type_breadcrumbs)
        if mode_action in ("back", "return"):
            return mode_action if mode_action == "return" else None
        if mode_action == "exit":
            sys.exit()

        if mode_action is not None:
            action_func = dispatch_map.get(mode_action)
            if action_func:
                return action_func()
        return None


def root_menu(dev: Any, registry: Any):
    main_title = get_string("menu_main_title")
    type_breadcrumbs = f"{main_title} > {get_string('menu_root_type_title')}"

    dispatch_map = {
        "1": lambda: _root_action_menu(
            dev, registry, gki=False, root_type="magisk", breadcrumbs=type_breadcrumbs
        ),
        "2": lambda: _handle_ksu_mode(dev, registry, type_breadcrumbs),
        "3": lambda: _root_action_menu(
            dev, registry, gki=False, root_type="sukisu", breadcrumbs=type_breadcrumbs
        ),
        "4": lambda: _root_action_menu(
            dev, registry, gki=False, root_type="resukisu", breadcrumbs=type_breadcrumbs
        ),
    }

    while True:
        mode_menu = TerminalMenu(
            get_string("menu_root_type_title"), breadcrumbs=main_title
        )
        mode_menu.add_option("1", get_string("menu_root_type_magisk"))
        mode_menu.add_option("2", get_string("menu_root_type_ksu_next"))
        mode_menu.add_option("3", get_string("menu_root_type_sukisu"))
        mode_menu.add_option("4", get_string("menu_root_type_resukisu"))
        mode_menu.add_separator()
        mode_menu.add_option("b", get_string("menu_back"))
        mode_menu.add_option("x", get_string("menu_main_exit"))

        choice = mode_menu.ask(
            get_string("prompt_select"), get_string("err_invalid_selection")
        )

        if choice == "b":
            return
        if choice == "x":
            sys.exit()

        action_func = dispatch_map.get(choice)
        if action_func:
            if action_func() == "main":
                return


def _handle_update_check():
    ui.clear()
    ui.echo(get_string("act_update_checking"))

    current_version = _read_current_version()
    latest_version, latest_release, latest_prerelease = _get_latest_version(
        current_version
    )

    if latest_version:
        ui.echo(get_string("update_avail_title"))
        prompt_msg = get_string("update_avail_prompt").format(
            curr=current_version, new=latest_version
        )
        choice = input(prompt_msg).strip().lower()
        if choice == "y":
            ui.echo(get_string("update_open_web"))
            webbrowser.open("https://github.com/miner7222/LTBox/releases")
            sys.exit(0)
    else:
        if latest_release or latest_prerelease:
            ui.echo(get_string("act_update_not_found").format(version=current_version))
        else:
            ui.echo(get_string("act_update_error").format(e="Unknown version"))

    ui.echo("")
    input(get_string("press_enter_to_continue"))


def settings_menu(
    dev: Any,
    registry: Any,
    skip_adb: bool,
    skip_rollback: bool,
    target_region: str,
    settings_store: Any,
) -> Tuple[bool, bool, str]:
    main_title = get_string("menu_main_title")

    def _toggle_region():
        nonlocal target_region
        target_region = "ROW" if target_region == "PRC" else "PRC"
        settings_store.update(target_region=target_region)

    def _toggle_adb():
        nonlocal skip_adb
        skip_adb = not skip_adb
        dev.skip_adb = skip_adb

    def _toggle_rollback():
        nonlocal skip_rollback
        skip_rollback = not skip_rollback

    def _change_lang():
        cmd_info = registry.get("change_language")
        if cmd_info:
            cmd_info.func(
                breadcrumbs=f"{main_title} > {get_string('menu_settings_title')}"
            )

    action_handlers = {
        "toggle_region": _toggle_region,
        "toggle_adb": _toggle_adb,
        "toggle_rollback": _toggle_rollback,
        "change_lang": _change_lang,
        "check_update": _handle_update_check,
    }

    while True:
        skip_adb_state = "ON" if skip_adb else "OFF"
        skip_rb_state = "ON" if skip_rollback else "OFF"

        menu_items = menu_data.get_settings_menu_data(
            skip_adb_state, skip_rb_state, target_region
        )
        action = select_menu_action(
            menu_items, "menu_settings_title", breadcrumbs=main_title
        )

        if action in ("back", "return"):
            return skip_adb, skip_rollback, target_region

        if action is not None:
            action_func = action_handlers.get(action)
            if action_func:
                action_func()


def prompt_for_language(
    force_prompt: bool = False,
    settings_store: Any = None,
    breadcrumbs: Optional[str] = None,
) -> str:
    if settings_store is None:
        settings_store = SETTINGS_STORE

    if not force_prompt:
        settings = settings_store.load()
        saved_lang = settings.language

        if saved_lang:
            try:
                available_languages = i18n.get_available_languages()
                avail_codes = [code for code, _ in available_languages]

                if saved_lang in avail_codes:
                    return saved_lang
            except Exception:
                pass

    i18n.load_lang("en")

    try:
        available_languages = i18n.get_available_languages()
    except RuntimeError as e:
        print(get_string("err_lang_generic").format(e=e), file=sys.stderr)
        input(get_string("press_enter_to_continue"))
        raise e

    menu = TerminalMenu(get_string("menu_lang_title"), breadcrumbs=breadcrumbs)
    lang_map = {}

    for i, (lang_code, lang_name) in enumerate(available_languages, 1):
        key = str(i)
        lang_map[key] = lang_code
        menu.add_option(key, lang_name)

    prompt = get_string("prompt_select").format(len=len(lang_map))
    error_msg = get_string("err_invalid_selection").format(len=len(lang_map))

    choice = menu.ask(prompt, error_msg)
    selected_lang = lang_map[choice]

    settings_store.update(language=selected_lang)

    return selected_lang


def main_loop(
    device_controller_class: Any,
    registry: Any,
    settings_store: Any,
):
    settings = settings_store.load()

    state = {
        "skip_adb": False,
        "skip_rollback": False,
        "target_region": settings.target_region,
    }
    dev = device_controller_class(skip_adb=state["skip_adb"])

    def _run_settings():
        state["skip_adb"], state["skip_rollback"], state["target_region"] = (
            settings_menu(
                dev,
                registry,
                state["skip_adb"],
                state["skip_rollback"],
                state["target_region"],
                settings_store,
            )
        )

    menu_handlers = {
        "menu_settings": _run_settings,
        "menu_root": lambda: root_menu(dev, registry),
        "menu_advanced": lambda: advanced_menu(dev, registry, state["target_region"]),
    }

    while True:
        menu_items = menu_data.get_main_menu_data(state["target_region"])
        action = select_menu_action(menu_items, "menu_main_title")

        if action is not None:
            action_func = menu_handlers.get(action)
            if action_func:
                action_func()
            else:
                extras: Dict[str, Any] = {}
                if action in ["patch_all", "patch_all_wipe"]:
                    extras["skip_rollback"] = state["skip_rollback"]
                    extras["target_region"] = state["target_region"]
                run_task(action, dev, registry, extra_kwargs=extras)
