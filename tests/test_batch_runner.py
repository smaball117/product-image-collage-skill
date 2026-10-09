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
                 "IMG_8846-2.jpg", "IMG_8848-3.jpg", "IMG_8849-4.jpg",
                 "IMG_8847-5.jpg", "IMG_8850.jpg", "OTHER-1.jpg",
                 "0N2A0873-3.png", "0N2A0873-5.png")
        self.command("check", "--tools", self.tools, "--category", "内裤",
                     "--images", self.base / "products")
        self.prepare("内裤")
        batch = self.out / "2026-10-08_underwear"
        encoded = (batch / "图片汇总.csv").read_bytes()
        self.assertTrue(encoded.startswith(b"\xff\xfe"), "Missing UTF-16 LE BOM")
        with (batch / "图片汇总.csv").open(encoding="utf-16", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, [
                "货号", "颜色", "@正面png", "@背面png",
                "@印花", "@裤口", "@裤边", "@裤腰"
            ], "内裤输出必须严格为 8 列且顺序固定")
            records = list(reader)
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertTrue(row["@正面png"].endswith("0N2A0873-1.png"))
        self.assertTrue(row["@背面png"].endswith("0N2A0873-2.png"))
        self.assertTrue(row["@印花"].endswith("IMG_8847-5.jpg"))
        self.assertTrue(row["@裤口"].endswith("IMG_8846-2.jpg"))
        self.assertTrue(row["@裤边"].endswith("IMG_8848-3.jpg"))
        self.assertTrue(row["@裤腰"].endswith("IMG_8849-4.jpg"))
        self.assertEqual(json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))["stage"], "waiting_indesign")
        self.assertTrue((self.input / "0N2A0873-1.png").exists())
        visible = sorted(p.name for p in batch.iterdir() if not p.name.startswith("."))
        self.assertEqual(visible, ["图片汇总.csv"], "第1步只应提供一张 CSV 表格")

    def test_underwear_set_exact_columns_ignores_unnumbered_back(self):
        self.add("top-1.png", "bottom-2.png",
                 "neck-1.jpg", "sleeve-2.jpg", "shoulder-3.jpg",
                 "waist-4.jpg", "0N2A6666.png", "0N2A6668.png")
        self.prepare("内衣套")
        batch = self.out / "2026-10-08_underwear-set"
        state = json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "waiting_indesign")
        self.assertEqual(state["unresolved"], {})
        with (batch / "图片汇总.csv").open(encoding="utf-16", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, [
                "货号", "颜色", "@上衣png", "@下衣png",
                "@领口", "@袖口", "@肩线", "@裤腰"
            ], "内衣套输出必须严格为 8 列且顺序固定")
            row = list(reader)[0]
        self.assertTrue(row["@上衣png"].endswith("top-1.png"))
        self.assertTrue(row["@下衣png"].endswith("bottom-2.png"))
        self.assertTrue(row["@领口"].endswith("neck-1.jpg"))
        self.assertTrue(row["@袖口"].endswith("sleeve-2.jpg"))
        self.assertTrue(row["@肩线"].endswith("shoulder-3.jpg"))
        self.assertTrue(row["@裤腰"].endswith("waist-4.jpg"))
        self.assertNotIn("@上衣背面", row)
        self.assertNotIn("@裤子背面", row)

    def test_duplicate_slot_requires_confirmation_then_collision_suffix(self):
        self.add("top-1.png", "top2-1.png", "bottom-2.png",
                 "neck-1.jpg", "sleeve-2.jpg",
                 "shoulder-3.jpg", "waist-4.jpg")
        self.prepare("内衣套")
        batch = self.out / "2026-10-08_underwear-set"
        state = json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stage"], "needs_mapping")
        self.assertIn("上衣png", state["unresolved"]["0N2A0873/01_浅水蓝"])
        self.assertFalse((batch / "图片汇总.csv").exists())
        self.assertTrue((batch / "图片汇总_待确认.csv").exists())
        overrides = self.base / "override.json"
        overrides.write_text(json.dumps({
            "0N2A0873/01_浅水蓝": {"上衣png": "top-1.png"}
        }, ensure_ascii=False), encoding="utf-8")
        self.prepare("内衣套", "--overrides", overrides)
        ready = self.out / "2026-10-08_underwear-set-02"
        self.assertTrue((ready / "图片汇总.csv").exists())

    def test_bundled_tools_and_auto_detect_underwear(self):
        self.add("0N2A0873-1.png", "0N2A0873-2.png",
                 "detail-5.jpg", "detail-2.jpg", "detail-3.jpg", "detail-4.jpg")
        args = ("--images", self.base / "products", "--output-root", self.out,
                "--date", "2026-10-08")
        self.command("check", "--images", self.base / "products")
        self.command("prepare", *args)
        batch = self.out / "2026-10-08_underwear"
        self.assertTrue((batch / "图片汇总.csv").is_file())
        state = json.loads((batch / ".skill" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual(state["category"], "underwear")
        self.assertEqual(Path(state["tools"]), REPO / "scripts")
        with (batch / "图片汇总.csv").open(encoding="utf-16", newline="") as stream:
            self.assertEqual(next(csv.reader(stream)), [
                "货号", "颜色", "@正面png", "@背面png", "@印花", "@裤口", "@裤边", "@裤腰"
            ])

    def test_bundled_tools_and_auto_detect_underwear_set(self):
        self.add("top-1.png", "pants-2.png",
                 "neck-1.jpg", "cuff-2.jpg", "seam-3.jpg", "waist-4.jpg")
        self.command("prepare", "--images", self.base / "products",
                     "--output-root", self.out, "--date", "2026-10-08")
        batch = self.out / "2026-10-08_underwear-set"
        self.assertTrue((batch / "图片汇总.csv").exists())
        with (batch / "图片汇总.csv").open(encoding="utf-16", newline="") as stream:
            self.assertEqual(next(csv.reader(stream)), [
                "货号", "颜色", "@上衣png", "@下衣png", "@领口", "@袖口", "@肩线", "@裤腰"
            ])

    def test_auto_detect_ambiguous_requires_category(self):
        self.add("top-1.png", "pants-2.png", "neck-1.jpg", "print-5.jpg")
        result = subprocess.run([
            sys.executable, str(RUNNER), "prepare", "--images",
            str(self.base / "products"), "--output-root", str(self.out)
        ], capture_output=True, text=True, timeout=25)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())

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
