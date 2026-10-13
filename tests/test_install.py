import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_install', ROOT / 'scripts' / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTest(unittest.TestCase):
    def test_fresh_install_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'skills'
            installer.install(dest, installer.SKILLS)
            for name in installer.SKILLS:
                self.assertEqual(installer.files(dest / name), installer.files(ROOT / 'skills' / name))
            installer.install(dest, installer.SKILLS)
            self.assertFalse((dest.parent / 'skill-backups').exists())
            self.assertTrue((dest / 'do-tsinghua-homework' / 'SKILL.md').is_file())

    def test_existing_edits_are_protected_then_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'skills'
            name = installer.SKILLS[0]
            installer.install(dest, [name])
            path = dest / name / 'SKILL.md'
            path.write_text('My local modifications', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                installer.install(dest, [name])
            self.assertEqual(path.read_text(), 'My local modifications')
            installer.install(dest, [name], replace=True)
            backups = list((dest.parent / 'skill-backups').glob(f'*/{name}/SKILL.md'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), 'My local modifications')
            self.assertEqual(path.read_bytes(), (ROOT / 'skills' / name / 'SKILL.md').read_bytes())

    def test_dry_run_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'not-created'
            installer.install(dest, installer.SKILLS, dry_run=True)
            self.assertFalse(dest.exists())


if __name__ == '__main__':
    unittest.main()
