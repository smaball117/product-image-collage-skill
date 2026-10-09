"""Offline checks of the Windows InDesign COM bridge.

These tests validate generation and guardrails only, not the Adobe GUI.
"""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / "scripts" / "indesign_merge.py"
SPEC = importlib.util.spec_from_file_location("merge_bridge", DRIVER)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class InDesignMergeDriverTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        root = Path(self.work.name)
        self.template = root / "测试模板.indd"
        self.template.write_bytes(b"placeholder for offline dry-run only")
        self.csv = root / "数据合并.csv"
        self.output = root / "拼图_待人工调整.indd"
        self.fields = ["货号", "颜色", "@正面png", "@背面png",
                       "@印花", "@裤口", "@裤边", "@裤腰"]
        self.image = root / "sample.png"
        self.image.write_bytes(b"sample image path exists for dry run")

    def write_csv(self, columns):
        with self.csv.open("w", encoding="utf-16", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerow(["01", "浅蓝"] + [str(self.image)] * (len(columns) - 2))

    def test_generate_windows_com_jsx_without_running_indesign(self):
        self.write_csv(self.fields)
        result = module.merge(self.template, self.csv, self.output, dry_run=True)
        script = result["script"]
        self.assertIn("dataMergeProperties", script)
        self.assertIn("selectDataSource(csv)", script)
        self.assertIn("RecordSelection.ALL_RECORDS", script)
        self.assertIn("mergeRecords()", script)
        self.assertIn("merged.save(target)", script)
        self.assertIn("UserInteractionLevels.NEVER_INTERACT", script)
        self.assertIn("savedInteractionLevel = app.scriptPreferences.userInteractionLevel", script)
        self.assertIn("app.scriptPreferences.userInteractionLevel = savedInteractionLevel", script)
        self.assertNotIn(
            "app.scriptPreferences.userInteractionLevel = UserInteractionLevels.INTERACT_WITH_ALL;",
            script,
            "不得强制修改用户原有的 InDesign 交互级别",
        )
        self.assertIn('stage = "select_csv_data_source"', script)
        self.assertIn('stage = "merge_all_records"', script)
        self.assertIn("finally {", script)
        self.assertIn("verify_template_links", script)
        self.assertIn("LinkStatus.LINK_MISSING", script)
        self.assertIn("step=", script)
        self.assertIn("拼图", self.output.name)
        self.assertIn("\\u62fc", script)  # path uses unicode escape sequences
        self.assertNotIn("__JOB_JSON__", script)
        self.assertFalse(self.output.exists())

    def test_existing_modal_dialog_reports_actionable_error(self):
        """COM can fail before JSX starts, so a JSX dialog setting alone is insufficient."""
        from unittest.mock import patch
        import subprocess

        self.write_csv(self.fields)
        failed_com = subprocess.CompletedProcess(
            args=["powershell.exe"], returncode=1, stdout="",
            stderr="InDesign: modal dialog or alert is active",
        )
        with patch.object(module.platform, "system", return_value="Windows"):
            with patch.object(module.subprocess, "run", return_value=failed_com):
                with self.assertRaisesRegex(RuntimeError, "已有未关闭的模态对话框"):
                    module.merge(self.template, self.csv, self.output)
        self.assertFalse(self.output.exists())

    def test_reject_bad_csv_headers(self):
        self.write_csv(["货号", "颜色", "@one"])
        with self.assertRaises(ValueError):
            module.merge(self.template, self.csv, self.output, dry_run=True)

    def test_preflight_fails_for_missing_images(self):
        self.write_csv(self.fields)
        self.image.unlink()
        with self.assertRaisesRegex(ValueError, "图片不存在"):
            module.merge(self.template, self.csv, self.output, dry_run=True)
        self.assertFalse(self.output.exists())

    def test_preflight_fails_for_empty_image_cell(self):
        with self.csv.open("w", encoding="utf-16", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(self.fields)
            writer.writerow(["01", "浅蓝"] + [""] * 6)
        with self.assertRaisesRegex(ValueError, "为空"):
            module.merge(self.template, self.csv, self.output, dry_run=True)

    def test_refuse_overwrite_existing_merged_document(self):
        self.write_csv(self.fields)
        self.output.write_bytes(b"existing designer changes")
        with self.assertRaises(FileExistsError):
            module.merge(self.template, self.csv, self.output, dry_run=True)


if __name__ == "__main__":
    unittest.main()
