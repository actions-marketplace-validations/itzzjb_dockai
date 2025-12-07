import contextlib

from dockai.cli import ui


class DummyConsole:
    def __init__(self):
        self.messages = []
    def print(self, *args, **kwargs):
        self.messages.append((args, kwargs))
    def status(self, message, spinner=None):
        return contextlib.nullcontext()


def test_setup_logging_verbose_sets_debug(monkeypatch):
    fake_console = DummyConsole()
    monkeypatch.setattr(ui, "console", fake_console)
    logger = ui.setup_logging(verbose=True)
    assert logger.name == "dockai"


def test_display_summary_outputs_usage(monkeypatch):
    fake_console = DummyConsole()
    monkeypatch.setattr(ui, "console", fake_console)

    final_state = {
        "retry_history": [{"lesson_learned": "note"}],
        "usage_stats": [{"total_tokens": 10, "stage": "analyze"}, {"total_tokens": 5, "stage": "generate"}],
        "current_plan": {"base_image_strategy": "use-slim", "use_multi_stage": False},
    }
    ui.display_summary(final_state, "/tmp/Dockerfile")

    printed = "".join(str(args) for args, _ in fake_console.messages)
    assert "Dockerfile" in printed
    # Inspect Panel payload for usage summary
    panels = [args[0] for args, _ in fake_console.messages if args and hasattr(args[0], "renderable")]
    assert panels, "Expected a summary panel to be printed"
    render_text = "\n".join(str(p.renderable) for p in panels)
    assert "Total Tokens" in render_text
    assert "analyze" in render_text


def test_display_failure_shows_error_details(monkeypatch):
    fake_console = DummyConsole()
    monkeypatch.setattr(ui, "console", fake_console)

    final_state = {
        "error_details": {
            "error_type": "project_error",
            "message": "bad config",
            "suggestion": "fix it",
        },
        "retry_count": 1,
        "max_retries": 3,
        "retry_history": [{"what_was_tried": "a", "why_it_failed": "b"}],
        "usage_stats": [{"total_tokens": 2, "stage": "analyze"}],
    }

    ui.display_failure(final_state)

    panels = [args[0] for args, _ in fake_console.messages if args and hasattr(args[0], "renderable")]
    assert panels, "Expected an error panel"
    render_text = "\n".join(str(p.renderable) for p in panels)
    printed = "".join(str(args) for args, _ in fake_console.messages)
    assert "bad config" in render_text
    assert "fix it" in render_text
    assert "retri" in printed.lower()
    assert "tokens" in printed.lower()
