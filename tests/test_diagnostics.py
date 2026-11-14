import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from diagnostics import _stack_only, install


class DiagnosticsPrivacyTests(unittest.TestCase):
    def test_exception_message_is_not_serialized(self):
        secret = "typed-private-message-should-not-appear"
        try:
            raise RuntimeError(secret)
        except RuntimeError as exc:
            output = _stack_only(type(exc), exc.__traceback__)
        self.assertNotIn(secret, output)
        self.assertIn("RuntimeError", output)

    @unittest.skipIf(os.name == "nt", "POSIX file mode bits are not enforced by Windows")
    def test_diagnostics_directory_is_private(self):
        import stat
        with tempfile.TemporaryDirectory() as folder:
            log_dir = install(folder)
            self.assertEqual(stat.S_IMODE(os.stat(log_dir).st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(log_dir, "application.log")).st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
