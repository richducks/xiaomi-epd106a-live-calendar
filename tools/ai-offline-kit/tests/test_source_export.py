import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'host_source_backup.py'


class TestSourceExport(unittest.TestCase):
    def test_portable_source_archive_excludes_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / 'source'
            project.mkdir()
            (project / '.git').mkdir()
            (project / '.git' / 'config').write_text('private git config', encoding='utf-8')
            (project / 'app.py').write_text('print("hello")', encoding='utf-8')
            output = base / 'source_backup.zip'
            proc = subprocess.run([sys.executable, str(SCRIPT), '--project-dir', str(project),
                                   '--output', str(output)], capture_output=True, text=True, timeout=35)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            with zipfile.ZipFile(output) as z:
                self.assertIn('project/app.py', z.namelist())
                self.assertFalse(any(x.startswith('project/.git/') for x in z.namelist()))

    def test_refuse_export_into_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            output = source / 'export.zip'
            proc = subprocess.run([sys.executable, str(SCRIPT), '--project-dir', str(source),
                                   '--output', str(output)], capture_output=True, text=True, timeout=35)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
