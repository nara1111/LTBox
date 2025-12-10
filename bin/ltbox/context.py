from dataclasses import dataclass, field
from typing import Optional, Callable

from .device import DeviceController

@dataclass
class TaskContext:
    dev: DeviceController
    wipe: int = 0
    skip_rollback: bool = False
    device_model: Optional[str] = None
    active_slot_suffix: Optional[str] = None

    on_log: Callable[[str], None] = field(default_factory=lambda: lambda s: print(s))