import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing

PROJECT=Path(__file__).resolve().parents[1]

class MigrationTests(unittest.TestCase):
    def test_legacy_schema_copy_preserves_issued_records(self):
        # Run a copied migration tool in an isolated directory, using the old schema.
        import shutil
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);shutil.copy(PROJECT/'app.py',root/'app.py');shutil.copy(PROJECT/'migrate_v4.py',root/'migrate_v4.py')
            shutil.copytree(PROJECT/'assets',root/'assets')
            spec=importlib.util.spec_from_file_location('migration_fixture',root/'app.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
            legacy=root/'legacy.db';app.DB=legacy;app.init_db()
            with app.connect() as db:
                db.execute('ALTER TABLE questions DROP COLUMN accepted_answers')
                db.execute("INSERT INTO participants(name,normalized_name,last2,joined_at,question_ids,revision,completed_at,invite_code,checked_at) VALUES(?,?,?,?,?,?,?,?,?)",('홍길동','홍길동','07','2026-01-01','[1,2,3]',1,'2026-01-01','INJ-1234567890ABCDEF','2026-01-02'))
            before=hashlib.sha256(legacy.read_bytes()).hexdigest()
            run=subprocess.run([sys.executable,str(root/'migrate_v4.py'),str(legacy)],capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
            self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(),before)
            with closing(sqlite3.connect(root/'data/event_v5.db')) as db:
                row=db.execute('SELECT invite_code,checked_at FROM participants').fetchone()
                self.assertEqual(row,('INJ-1234567890ABCDEF','2026-01-02'))
                self.assertEqual(db.execute("SELECT count(*) FROM questions WHERE accepted_answers!='[]'").fetchone()[0],3)
            again=subprocess.run([sys.executable,str(root/'migrate_v4.py'),str(legacy)],capture_output=True)
            self.assertNotEqual(again.returncode,0)
