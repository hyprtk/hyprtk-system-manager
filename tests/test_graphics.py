import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager.panels import graphics
from system_manager.util import RunResult

SUMMARY = """
==========
VULKANINFO
==========

Devices:
========
GPU0:
	apiVersion         = 1.4.363
	driverVersion      = 26.3.1
	deviceType         = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
	deviceName         = AMD Radeon RX 6900 XT (RADV NAVI21)
	driverID           = DRIVER_ID_MESA_RADV
	driverName         = radv

GPU1:
	apiVersion         = 1.4.0
	deviceName         = llvmpipe (LLVM 20.1.8, 256 bits)
	driverName         = llvmpipe
"""


class GraphicsTests(unittest.TestCase):
    def test_parse_vulkan_summary(self):
        devices = graphics.parse_vulkan_summary(SUMMARY)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["devicename"], "AMD Radeon RX 6900 XT (RADV NAVI21)")
        self.assertEqual(devices[0]["drivername"], "radv")
        self.assertEqual(devices[0]["apiversion"], "1.4.363")
        self.assertEqual(devices[1]["devicename"], "llvmpipe (LLVM 20.1.8, 256 bits)")

    def test_parse_empty(self):
        self.assertEqual(graphics.parse_vulkan_summary(""), [])

    def test_vulkan_icds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "radeon_icd.json").write_text(
                json.dumps({"ICD": {"api_version": "1.4.363"}}))
            (root / "intel_icd.json").write_text("{}")
            with mock.patch.object(graphics, "ICD_DIRS", [root]):
                icds = graphics.vulkan_icds()
        self.assertEqual([item["name"] for item in icds],
                         ["intel_icd.json", "radeon_icd.json"])
        self.assertEqual(icds[1]["api"], "1.4.363")

    def test_icd_without_vulkaninfo_is_not_missing(self):
        with mock.patch.object(graphics, "vulkan_icds",
                               return_value=[{"name": "radeon_icd.json", "api": "1.4.363"}]), \
             mock.patch.object(graphics.util, "which", return_value=None), \
             mock.patch.object(graphics.util, "run",
                               return_value=RunResult(127, "", "missing")):
            page = graphics.probe()
        values = [row.get("value", "") for section in page["sections"]
                  for row in section["rows"] if row.get("type") == "info"]
        self.assertTrue(any("driver installed" in value for value in values))
        self.assertTrue(any("vulkan-tools" in row.get("text", "") for section in page["sections"]
                            for row in section["rows"] if row.get("type") == "note"))


if __name__ == "__main__":
    unittest.main()
