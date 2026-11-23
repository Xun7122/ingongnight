import itertools
import json
import tempfile
import unittest
from pathlib import Path
from test_event import mod

class StoryTests(unittest.TestCase):
    def test_custom_bank_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            old_db=mod.DB;mod.DB=Path(root)/'custom.db'
            try:
                mod.init_db()
                with mod.connect() as db:
                    db.execute("UPDATE questions SET prompt='운영진이 직접 쓴 문제' WHERE id=(SELECT min(id) FROM questions)")
                    db.execute('UPDATE config SET bank_version=5')
                mod.init_db()
                self.assertEqual(mod.list_questions()[0]['question'],'운영진이 직접 쓴 문제')
            finally:mod.DB=old_db
    def test_boxes_books_and_keys_have_unique_solutions(self):
        boxes=['달','별','왕관']
        self.assertEqual([x for x in boxes if sum([x=='달',x!='달',x!='왕관'])==1],['왕관'])
        orders=[x for x in itertools.permutations(['별','달','열쇠','왕관']) if x.index('달')==x.index('별')+1 and x.index('왕관') not in (0,3) and x.index('열쇠')>x.index('달')]
        self.assertEqual(orders,[('별','달','왕관','열쇠')])
        keys=[dict(zip(['붉은색','은빛','검은색'],x)) for x in itertools.permutations(boxes)]
        keys=[x for x in keys if x['은빛'] not in ('별','왕관') and x['검은색']!='왕관']
        self.assertEqual(keys,[{'붉은색':'왕관','은빛':'달','검은색':'별'}])
    def test_candy_claim_and_guards(self):
        models=[(g,r,c,m) for g,r,c,m in itertools.product([False,True],repeat=4) if (not c or g) and (not g or r) and (not c or m)]
        statements=[lambda g,r,c,m:not g or c,lambda g,r,c,m:not m or c,lambda g,r,c,m:m or not c,lambda g,r,c,m:not r or g]
        self.assertEqual([i for i,statement in enumerate(statements) if all(statement(*model) for model in models)],[2])
        possibilities=[]
        for correct,speaker_truthful in itertools.product([0,1],[False,True]):
            other_answer=1-correct if speaker_truthful else correct
            reported=other_answer if speaker_truthful else 1-other_answer
            if reported==0:possibilities.append(correct)
        self.assertEqual(set(possibilities),{1})
    def test_v5_default_bank_upgrade_preserves_completed_invites(self):
        with tempfile.TemporaryDirectory() as root:
            old_db=mod.DB;mod.DB=Path(root)/'legacy.db'
            try:
                mod.init_db()
                with mod.connect() as db:
                    for row,prompt in zip(db.execute('SELECT id FROM questions ORDER BY position,id').fetchall(),mod.LEGACY_V5_PROMPTS):db.execute('UPDATE questions SET prompt=? WHERE id=?',(prompt,row['id']))
                    db.execute('UPDATE config SET bank_version=5')
                    db.execute("INSERT INTO participants(name,normalized_name,last2,joined_at,question_ids,revision,completed_at,invite_code) VALUES(?,?,?,?,?,?,?,?)",('완료참가자','완료참가자','07','2026-01-01','[1,2,3]',1,'2026-01-01','INJ-0000000000000001'))
                mod.init_db()
                self.assertEqual(mod.list_questions(),[{**q,'accepted_answers':q.get('accepted_answers',[]),'image':q.get('image',''),'option_images':q.get('option_images',[])} for q in mod.DEFAULT_QUESTIONS])
                self.assertEqual(mod.lookup('완료참가자07')['invite_code'],'INJ-0000000000000001')
                with mod.connect() as db:self.assertEqual(db.execute('SELECT revision FROM config').fetchone()[0],2)
            finally:mod.DB=old_db
