from ltbox.main import CommandRegistry

def test_registry_registration():
    registry = CommandRegistry()

    def dummy_task(dev=None):
        return "success"

    registry.add(
        name="test_cmd",
        func=dummy_task,
        title="Test Command",
        require_dev=True,
        some_arg="value"
    )

    cmd = registry.get("test_cmd")
    assert cmd is not None
    assert cmd["title"] == "Test Command"
    assert cmd["require_dev"] is True
    assert cmd["default_kwargs"]["some_arg"] == "value"
    assert cmd["func"] == dummy_task
