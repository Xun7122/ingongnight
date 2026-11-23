"""Exercise real HTTP handlers on an ephemeral localhost server and isolated DB."""
import http.client
import json
import threading
from urllib.parse import quote
import unittest
import tempfile
from pathlib import Path
from test_event import mod

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        mod.DB=Path(self.tmp.name)/'test.db'
        mod.init_db()
    def tearDown(self):
        self.tmp.cleanup()
    def test_http_admin_and_qr_lifecycle(self):
        mod.PASSWORD='integration-test-password'
        server=mod.ThreadingHTTPServer(('127.0.0.1',0),mod.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        cookie='';csrf=''
        def request(path,data=None,auth=True,token=True):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=8)
            headers={}
            if cookie and auth:headers['Cookie']=cookie
            if csrf and token:headers['X-CSRF']=csrf
            if data is not None:headers['Content-Type']='application/json'
            c.request('POST' if data is not None else 'GET',path,json.dumps(data).encode() if data is not None else None,headers)
            r=c.getresponse();body=r.read();result=(r.status,dict(r.getheaders()),body);c.close();return result
        try:
            self.assertEqual(request('/')[0],200)
            self.assertEqual(request('/static/v5.css')[0],200)
            self.assertEqual(request('/static/invitation.css')[0],200)
            self.assertEqual(request('/static/invitation.js')[0],200)
            self.assertEqual(request('/static/fonts/NotoSerifKR.woff2')[0],200)
            self.assertEqual(request('/api/admin/state')[0],401)
            self.assertEqual(request('/api/admin/login',{'password':'wrong'})[0],403)
            status,h,body=request('/api/admin/login',{'password':mod.PASSWORD});self.assertEqual(status,200)
            cookie=h['Set-Cookie'].split(';')[0];csrf=json.loads(body)['csrf']
            self.assertEqual(request('/api/admin/search',{'query':'홍길동 07'},token=False)[0],403)
            status,_,body=request('/api/start',{'name':'홍길동','last2':'07'})
            questions=json.loads(body)['questions'];self.assertEqual(len(questions),3)
            self.assertNotIn('accepted_answers',json.loads(body)['questions'][0])
            with mod.connect() as db:qmap={r['id']:r for r in db.execute('SELECT * FROM questions')}
            answers=[json.loads(qmap[q['id']]['accepted_answers'])[0].replace('',' ') if q['kind']=='text' else qmap[q['id']]['answer'] for q in questions]
            _,_,body=request('/api/quiz',{'name':'홍길동','last2':'07','answers':answers});code=json.loads(body)['invite_code']
            self.assertEqual(request('/api/invite-art?code='+code)[0],200)
            status,_,body=request('/api/admin/qr.svg?url='+quote('https://example.com/invite',safe=''));self.assertEqual(status,200);self.assertIn(b'<svg',body)
            self.assertEqual(request('/api/admin/participants.csv')[0],200)
            self.assertEqual(request('/api/admin/search',{'query':code})[0],200)
            for query in ['홍길동','홍길동07','홍길동 07']:
                _,_,body=request('/api/admin/search',{'query':query})
                found=json.loads(body)['participants']
                self.assertEqual(len(found),1);self.assertEqual(found[0]['invite_code'],code)
            self.assertEqual(request('/api/admin/check',{'invite_code':code})[0],200)
            self.assertEqual(request('/api/admin/check',{'invite_code':code})[0],409)
            self.assertEqual(request('/api/admin/questions',{'questions':mod.list_questions()})[0],200)
            self.assertEqual(request('/api/admin/logout',{})[0],200)
            self.assertEqual(request('/api/admin/state')[0],401)
        finally:server.shutdown();server.server_close();thread.join()

