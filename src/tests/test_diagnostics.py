from app import diagnostics


def test_worker_diagnostic_contains_id_and_persistent_traceback(tmp_path):
    original_path = diagnostics._LOG_FILE
    original_handlers = list(diagnostics._LOG.handlers)
    try:
        diagnostics._LOG_FILE = None
        for handler in list(diagnostics._LOG.handlers):
            diagnostics._LOG.removeHandler(handler)

        path = diagnostics.configure_logging(tmp_path)
        try:
            raise RuntimeError("serial port disappeared")
        except RuntimeError as exc:
            message = diagnostics.report_exception("Firmware upload", exc)

        assert "Firmware upload failed" in message
        assert "serial port disappeared" in message
        assert "Diagnostic ID:" in message
        assert str(path) in message
        content = path.read_text(encoding="utf-8")
        assert "Traceback (most recent call last)" in content
        assert "RuntimeError: serial port disappeared" in content
    finally:
        for handler in list(diagnostics._LOG.handlers):
            diagnostics._LOG.removeHandler(handler)
            handler.close()
        diagnostics._LOG.handlers.extend(original_handlers)
        diagnostics._LOG_FILE = original_path
