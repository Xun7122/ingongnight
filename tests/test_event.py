"""v4 오프라인 검증: 이름+끝 두 자리, 사진 문제, 무제한 발급, 중복 발급 방지."""
import importlib.util
import tempfile
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inj_event_v4',PROJECT/'app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class EventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        mod.DB=Path(self.tmp.name)/'test.db'
        mod.init_db()
    def tearDown(self):self.tmp.cleanup()
    def complete(self,i):
        name='Tester'+chr(65+i//26)+chr(65+i%26)
        last2=f'{i%100:02d}'
        code, data = mod.start_participant(name,last2)
        self.assertEqual(code,200)
        if data['status']=='completed':return data
        with mod.connect() as db:
            qmap={r['id']:r for r in db.execute('SELECT * FROM questions')}
        answers=[json.loads(qmap[q['id']]['accepted_answers'])[0] if json.loads(qmap[q['id']]['accepted_answers']) else qmap[q['id']]['answer'] for q in data['questions']]
        code,data=mod.submit_quiz(name,last2,answers)
        self.assertEqual(code,200)
        return data
    def test_name_last2_inputs(self):
        self.assertTrue(mod.validate_person('홍길동','10'))
        self.assertTrue(mod.validate_person('Kim Min','05'))
        for name,suffix in [('홍','10'),('홍길동','1'),('홍길동','aa'),('홍길동','101'),('1234','34'),('', '11')]:
            self.assertFalse(mod.validate_person(name,suffix))
    def test_three_distinct_groups_have_images(self):
        _, data=mod.start_participant('홍길동','10')
        groups={q['group'] for q in data['questions']}
        self.assertEqual(groups,set(mod.QUIZ_GROUPS))
        proverb=next(q for q in data['questions'] if q['group']=='proverb')
        ticket=next(q for q in data['questions'] if q['group']=='ticket')
        self.assertTrue(proverb['image'])
        self.assertTrue(ticket['image'])
        self.assertEqual(proverb['kind'],'text')
        self.assertEqual(proverb['options'],[])
        self.assertTrue(all('accepted_answers' not in q for q in data['questions']))
        self.assertTrue(all('answer' not in q for q in data['questions']))
        chocolate=next(q for q in data['questions'] if q['group']=='chocolate')
        self.assertTrue(chocolate['image'])
    def test_completed_once_and_check_once(self):
        first=self.complete(1)
        self.assertEqual(first['status'],'completed')
        again=self.complete(1)
        self.assertEqual(again['invite_code'],first['invite_code'])
        self.assertEqual(mod.mark_checked(first['invite_code'])[0],200)
        self.assertEqual(mod.mark_checked(first['invite_code'])[0],409)
        self.assertEqual(mod.admin_dashboard()['counts']['checked'],1)
    def test_wrong_answers_retry(self):
        _,data=mod.start_participant('홍길동','10')
        with mod.connect() as db:
            qmap={r['id']:r for r in db.execute('SELECT * FROM questions')}
        wrong=['오답' if q['kind']=='text' else (qmap[q['id']]['answer']+1)%len(q['options']) for q in data['questions']]
        status,ret=mod.submit_quiz('홍길동','10',wrong)
        self.assertEqual((status,ret['status']),(200,'retry'))
        self.assertEqual(ret['missed'],[0,1,2])
        self.assertEqual(mod.admin_dashboard()['counts']['completed'],0)
    def test_unlimited_concurrent_135(self):
        with ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(self.complete,range(135)))
        codes=[x['invite_code'] for x in results]
        self.assertEqual(len(set(codes)),135)
        self.assertEqual(mod.admin_dashboard()['counts']['completed'],135)
        self.assertNotIn('remaining',mod.admin_dashboard()['counts'])
    def test_questions_editor(self):
        questions=mod.list_questions()
        self.assertEqual(len(questions),9)
        self.assertEqual(mod.update_questions(questions)[0],200)
        self.assertEqual(len(mod.list_questions()),len(questions))
        bad=[x for x in questions if x['group']!='ticket']
        self.assertEqual(mod.update_questions(bad)[0],400)
        q2=[dict(x) for x in questions]
        q2[0]['image']='../../.env'
        self.assertEqual(mod.update_questions(q2)[0],400)

    def test_text_spacing_and_no_choice_bypass(self):
        with mod.connect() as db:
            for q in db.execute("SELECT * FROM questions WHERE group_key='proverb'"):
                answer=json.loads(q['accepted_answers'])[0]
                self.assertTrue(mod.answer_matches(q,' \t'.join(answer)))
                self.assertFalse(mod.answer_matches(q,0))
                self.assertFalse(mod.answer_matches(q,'무관한 답'))
    def test_malformed_payloads(self):
        for answers in [None,[],[True,0,0],[' '*4,0,0],[{},0,0],['x'*101,0,0]]:
            self.assertEqual(mod.submit_quiz('홍길동','10',answers)[0],400)
    def test_revision_and_issued_invitation_survive_edits(self):
        done=self.complete(1)
        mod.start_participant('미완료','02')
        self.assertEqual(mod.update_questions(mod.list_questions())[0],200)
        self.assertEqual(mod.submit_quiz('미완료','02',['작심삼일',0,0])[0],409)
        _,again=mod.start_participant('TesterAB','01')
        self.assertEqual(again['invite_code'],done['invite_code'])

if __name__=='__main__':unittest.main()
