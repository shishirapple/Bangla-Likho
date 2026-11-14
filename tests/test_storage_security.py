import os
import stat
import tempfile
import unittest
from engine import save_json, load_json


class LocalStorageSecurityTests(unittest.TestCase):
    def test_json_write_is_atomic_and_round_trips(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "config.json")
            value = {"theme": "dark", "adaptive_learning": False}
            save_json(path, value)
            self.assertEqual(load_json(path, {}), value)
            self.assertFalse(os.path.exists(path + ".tmp"))

    @unittest.skipIf(os.name == "nt", "POSIX file mode bits are not enforced by Windows")
    def test_local_json_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "private.json")
            save_json(path, {"local": True})
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
