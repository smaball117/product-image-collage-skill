"""Ensure the exact original InDesign templates are included in the Skill.

The first local pilot is still required to prove InDesign data merge works.
"""
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {
    "内衣套数据合并模板.indd": "be1c4ba81fbcb50bbcf1047495b8508843dfc258fb3acf00720a14e79c9bd57c",
    "内裤数据合并模板-最终版.indd": "6b57a0e097b2b31665a301ad817b1701f9a51a68a98a5335f514222613e93aab",
}

class BundledInDesignTemplateTests(unittest.TestCase):
    def test_template_integrity(self):
        for name, expected in TEMPLATES.items():
            with self.subTest(name=name):
                path = ROOT / "assets" / "indesign" / name
                self.assertTrue(path.is_file(), f"Template missing: {name}")
                data = path.read_bytes()
                self.assertGreater(len(data), 100_000, f"Template unexpectedly small: {name}")
                digest = hashlib.sha256(data).hexdigest()
                self.assertEqual(digest, expected, f"Template contents differ: {name}")

if __name__ == "__main__":
    unittest.main()
