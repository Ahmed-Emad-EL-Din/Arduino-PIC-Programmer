from pathlib import Path
from tempfile import TemporaryDirectory

from core.firmware_source import FirmwareSourceStore


def test_firmware_source_saves_and_resets_to_bundled_default():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        bundled = root / "source" / "ProgramPic.ino"
        custom = root / "user" / "ProgramPic.ino"
        bundled.parent.mkdir()
        bundled.write_text("void setup() {}\n", encoding="utf-8")
        store = FirmwareSourceStore(bundled, custom)

        assert store.load() == "void setup() {}\n"
        assert not store.has_custom_source
        store.save("void setup() { Serial.begin(115200); }\n")
        assert store.has_custom_source
        assert store.load().endswith("Serial.begin(115200); }\n")
        store.reset()
        assert not store.has_custom_source
        assert store.load() == "void setup() {}\n"


def test_firmware_source_export_uses_selected_sketch_path():
    with TemporaryDirectory() as directory:
        destination = Path(directory) / "ProgramPic" / "ProgramPic.ino"
        FirmwareSourceStore.export("// custom sketch\n", destination)
        assert destination.read_text(encoding="utf-8") == "// custom sketch\n"
