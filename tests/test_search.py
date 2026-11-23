import tempfile
import unittest
from pathlib import Path
from test_event import mod

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();mod.DB=Path(self.tmp.name)/'test.db';mod.init_db()
        mod.start_participant('김지민','07');mod.start_participant('김지민','19');mod.start_participant('김지수','02')
    def tearDown(self):self.tmp.cleanup()
    def test_name_search_returns_every_match_without_guessing_identity(self):
        rows,truncated=mod.search_participants('김지민')
        self.assertFalse(truncated);self.assertEqual({x['last2'] for x in rows},{'07','19'})
        self.assertEqual(len(mod.search_participants('김지')[0]),3)
    def test_suffix_with_and_without_space_and_leading_zero(self):
        for text in ['김지민 07','김지민07','  김지민   07  ']:
            rows,_=mod.search_participants(text);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['last2'],'07')
        self.assertEqual(mod.search_participants('김지민 08')[0],[])
    def test_empty_invalid_unknown_and_injection(self):
        for query in [None,'','  ','없는참가자','INJ-invalid',"' OR 1=1 --",'김'*51]:
            self.assertEqual(mod.search_participants(query)[0],[])
    def test_many_results_are_bounded_and_flagged(self):
        for i in range(55):mod.start_participant('모임'+chr(65+i//26)+chr(65+i%26),f'{i%100:02d}')
        rows,truncated=mod.search_participants('모임');self.assertEqual(len(rows),50);self.assertTrue(truncated)
