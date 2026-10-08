"""Zero-network regression tests for the batch adapter using mock external tools."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "batch_runner.py"


class BatchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.tools = self.base / "tools"
        self.tools.mkdir()
        (self.tools / "scan_product_images.py").write_text(
            "import re\n"
            "def match_image_number(name):\n"
            " m = re.search(r'-(\\d+)(?=\\.[^.]+$)', name)\n"
            " return (m.group(1), 'hyphen') if m else (None, None)\n",
            encoding="utf-8")
        (self.tools / "ocr_rename_images.py").write_text(
            "def init_ocr(): return object()\n"
            "def extract_text_from_image(ocr, path): return '测试颜色'\n"
            "def clean_to_filename(t): return t\n", encoding="utf-8")
        (self.tools / "batch_add_white_mask.py").write_text(
            "from pathlib import Path\n"
            "def process_image(p, out):\n"
            " (Path(out) / (Path(p).stem + '.png')).write_bytes(b'masked')\n"
            " return True\n", encoding="utf-8")
        self.input = self.base / "products" / "0N2A0873" / "01_浅水蓝"
        self.input.mkdir(parents=True)
        self.out = self.base / "batches"

    def command(self, *args):
        result = subprocess.run([sys.executable, str(RUNNER), *map(str, args)],
                                capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def add(self, *names):
        for name in names:
            (self.input / name).write_bytes(b"fake original image data")

    def prepare(self, category, *extra):
        return self.command("prepare", "--images", self.base / "products",
                            "--tools", self.tools, "--category", category,
                            "--output-root", self.out, "--date", "2026-10-08", *extra)

    def test_check_and_underwear_csv_encoding(self):
        self.add("0N2A0873-1.png", "0N2A0873-2.png",
                 "IMG_8846-2.jpg", "IMG_8850.jpg", "OTHER-1.jpg")
        self.command("check", "--tools", self.tools, "--category", "内裤",
                     "--images", self.base / "products")
        self.prepare("内裤")
        batch = self.out / "2026-10-08_underwear"
        encoded = (batch / "图片汇总.csv").read_bytes()
        self.assertTrue(encoded.startswith(b"\xff\xfe"), "Missing UTF-16 LE BOM")
        with (batch / "图片汇总.csv").open(encoding="utf-16", newline="") as stream:
            records = list(csv.DictReader(stream))
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertIn("@内裤正面", row)
        self.assertTrue(row["@内裤正面"].endswith("0N2A0873-1.png"))
        self.assertTrue(row["@内裤背面"].endswith("0N2A0873-2.png"))
        self.assertTrue(row["@裤口细节"].endswith("IMG_8846-2.jpg"))
        self.assertTrue(row["@其他细节"].endswith("IMG_8850.jpg"))
        self.assertEqual(json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))["stage"], "waiting_indesign")
        self.assertTrue((self.input / "0N2A0873-1.png").exists())
        visible = sorted(p.name for p in batch.iterdir() if not p.name.startswith("."))
        self.assertEqual(visible, ["图片汇总.csv"], "第1步只应提供一张 CSV 表格")

    def test_unnumbered_back_not_guessed(self):
        self.add("top-1.png", "bottom-2.png", "0N2A6666.png", "0N2A6668.png")
        self.prepare("内衣套")
        batch = self.out / "2026-10-08_underwear-set"
        state = json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "needs_mapping")
        self.assertIn("0N2A0873/01_浅水蓝", state["unresolved"])
        self.assertFalse((batch / "图片汇总.csv").exists())
        with (batch / "图片汇总_待确认.csv").open(encoding="utf-16", newline="") as stream:
            row = list(csv.DictReader(stream))[0]
        self.assertEqual(row["@上衣背面"], "")
        self.assertEqual(row["@裤子背面"], "")

    def test_explicit_back_mapping_and_collision_name(self):
        self.add("top-1.png", "bottom-2.png", "0N2A6666.png", "0N2A6668.png")
        overrides = self.base / "override.json"
        overrides.write_text(json.dumps({
            "0N2A0873/01_浅水蓝": {
                "上衣背面": "0N2A6666.png",
                "裤子背面": "0N2A6668.png"
            }
        }, ensure_ascii=False), encoding="utf-8")
        self.prepare("内衣套", "--overrides", overrides)
        batch = self.out / "2026-10-08_underwear-set"
        state = json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "waiting_indesign")
        self.prepare("内衣套", "--overrides", overrides)
        self.assertTrue((self.out / "2026-10-08_underwear-set-02").exists())

    def test_resume_preserves_originals(self):
        self.add("0N2A0873-1.png", "0N2A0873-2.png")
        self.prepare("内裤")
        batch = self.out / "2026-10-08_underwear"
        raw = self.base / "ID-exports"
        raw.mkdir()
        (raw / "page-001.jpg").write_bytes(b"unchanged")
        self.command("resume", "--batch", batch, "--exported", raw)
        self.assertTrue((raw / "page-001.jpg").exists())
        self.assertEqual((raw / "page-001.jpg").read_bytes(), b"unchanged")
        self.assertTrue((batch / ".skill" / "exported" / "page-001.jpg").exists())
        self.assertTrue((batch / ".skill" / "renamed" / "测试颜色.jpg").exists())
        self.assertTrue((batch / "最终图片" / "测试颜色.png").exists())


if __name__ == "__main__":
    unittest.main()
