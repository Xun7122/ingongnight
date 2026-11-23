"""WSGI entrypoint; delegates to the existing tested request handlers."""
from __future__ import annotations
import io
import os
import threading
from email.message import Message
from flask import Flask,Response,request
import app as event

app=Flask(__name__,static_folder=None)
app.config['MAX_CONTENT_LENGTH']=100000
_ready=False
_init_lock=threading.Lock()


def ensure_ready():
    global _ready
    if _ready:return
    with _init_lock:
        if _ready:return
        if os.environ.get('VERCEL') and (not event.DATABASE_URL or not event.PASSWORD):
            raise RuntimeError('Cloud database and admin password must be configured')
        if not event.PASSWORD:raise RuntimeError('ADMIN_PASSWORD is required')
        event.init_db();_ready=True


class Bridge(event.Handler):
    def send_data(self,status,content,mime,headers=None,cache=False):
        security={
          'Content-Type':mime,'Cache-Control':'public, max-age=3600' if cache else 'no-store',
          'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY',
          'Referrer-Policy':'no-referrer',
          'Content-Security-Policy':"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}
        security.update(headers or {})
        self.result=Response(content,status=status,headers=security)


@app.route('/',defaults={'path':''},methods=['GET','POST','HEAD'])
@app.route('/<path:path>',methods=['GET','POST','HEAD'])
def route(path):
    try:ensure_ready()
    except Exception:
        app.logger.error('Event initialization failed; verify database and secret configuration')
        return Response('{"error":"서비스 연결을 준비 중입니다. 잠시 후 다시 시도해 주세요."}',503,
                        content_type='application/json; charset=utf-8',headers={'Cache-Control':'no-store'})
    if path=='api/health':return {'ok':True,'storage':'postgres' if event.DATABASE_URL else 'sqlite'}
    handler=Bridge.__new__(Bridge)
    handler.path=request.full_path.rstrip('?')
    handler.command='GET' if request.method=='HEAD' else request.method
    handler.headers=Message()
    for key,value in request.headers.items():handler.headers[key]=value
    handler.rfile=io.BytesIO(request.get_data())
    handler.client_address=(request.remote_addr or 'unknown',0)
    try:
        if handler.command=='POST':handler.do_POST()
        else:handler.do_GET()
        return handler.result
    except Exception:
        app.logger.error('Event request failed')
        return Response('{"error":"요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}',503,
                        content_type='application/json; charset=utf-8',headers={'Cache-Control':'no-store'})
