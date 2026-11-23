#!/usr/bin/env python3
"""인지용 × 인지용카 골든 티켓 v6: 행사장용 로컬 웹서버 (Python standard library)."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import unicodedata
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE = Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'vendor'))
STATIC = BASE / 'static'
ASSETS = BASE / 'assets'
DATA = BASE / 'data'
ENV = BASE / '.env'
QUIZ_GROUPS = ('proverb', 'ticket', 'chocolate')
GROUP_LABELS = {'proverb': '이미지 속담', 'ticket': '서재의 추리', 'chocolate': '봉인된 초대'}
QUIZ_LENGTH = 3
LOGIN_FAILURES = {}
FAIL_LOCK = threading.Lock()

LEGACY_V5_PROMPTS = ['사진 속 상황을 비유하는 속담을 적어 주세요. 눈앞의 세계를 전부라고 여기는 태도에 관한 표현입니다.', '사진이 표현하는 사자성어를 적어 주세요. 하나의 행동과 두 개의 결과 사이의 관계를 읽어 보세요.', '세 장면을 시간 순서대로 읽고, 전체를 설명하는 사자성어를 적어 주세요.', '네 장 모두 금색이지만 진짜는 하나입니다. 세 숫자의 합이 13이고, 곱이 56인 일련번호를 찾으세요.', '공장장은 “W 인장이 있으며, 세 자리 숫자가 왼쪽부터 커지고, 숫자의 합은 12”라고 적었습니다. 모든 조건을 만족하는 티켓은?', '아래 기록에서 정확히 한 사람만 사실을 말했습니다. 진짜 티켓은 어느 보관함에 있을까요?', '저울 기록을 보고 계산하세요. 같은 빈 상자 하나에 별 초콜릿 3개와 달 초콜릿 2개를 담으면 총 몇 g일까요?', '출고 기록의 모든 조건을 만족하도록, 마지막 빈칸에 들어갈 포장 수를 계산하세요.', '공장 규칙을 순서대로 적용하세요. 원료 18개로 시작했다면 마지막에 완성되는 초콜릿은 몇 개일까요?']

DEFAULT_QUESTIONS = [{'group': 'proverb',
  'question': '사진 속 상황을 비유하는 속담을 적어 주세요. 눈앞의 세계를 전부라고 여기는 태도에 관한 표현입니다.',
  'options': [],
  'answer': 0,
  'image': 'quiz-well.jpg',
  'accepted_answers': ['우물 안 개구리', '우물 안의 개구리']},
 {'group': 'proverb',
  'question': '사진이 표현하는 사자성어를 적어 주세요. 하나의 행동과 두 개의 결과 사이의 관계를 읽어 보세요.',
  'options': [],
  'answer': 0,
  'image': 'quiz-birds.jpg',
  'accepted_answers': ['일석이조']},
 {'group': 'proverb',
  'question': '세 장면을 시간 순서대로 읽고, 전체를 설명하는 사자성어를 적어 주세요.',
  'options': [],
  'answer': 0,
  'image': 'quiz-three-days.jpg',
  'accepted_answers': ['작심삼일']},
 {'group': 'ticket',
  'question': '“상자는 정직하지 않지만, 단서는 정직하지.” 달·별·왕관 상자 중 하나에 초대장이 있습니다. 세 문장 중 정확히 하나만 참이라면 어느 상자를 열어야 할까요?',
  'options': ['달 상자', '별 상자', '왕관 상자', '모두 비어 있다'],
  'answer': 2,
  'image': 'quiz-count-boxes.svg'},
 {'group': 'ticket',
  'question': '주인의 서재에 책 네 권이 놓여 있습니다. 쪽지의 조건을 모두 지키도록 다시 꽂으면, 왼쪽에서 세 번째 책의 표지는 무엇일까요?',
  'options': ['열쇠', '왕관', '별', '달'],
  'answer': 1,
  'image': 'quiz-count-books.svg'},
 {'group': 'ticket',
  'question': '“문에 맞는 열쇠는 하나씩뿐이네.” 붉은색·은빛·검은색 열쇠는 각각 다른 문을 엽니다. 왕관 문을 여는 열쇠를 골라 주세요.',
  'options': ['검은색 열쇠', '은빛 열쇠', '어떤 열쇠도 아니다', '붉은색 열쇠'],
  'answer': 3,
  'image': 'quiz-count-keys.svg'},
 {'group': 'chocolate',
  'question': '“긴 편지일수록 시작을 보게.” 서랍 안 쪽지의 각 줄에는 숨겨진 안내가 있습니다. 초대장이 기다리는 곳은 어디일까요?',
  'options': ['달빛 창가', '별빛 문 앞', '붉은 서랍', '시계 뒤'],
  'answer': 1,
  'image': 'quiz-count-letter.svg'},
 {'group': 'chocolate',
  'question': '주인은 사탕에 초대권을 숨겨 두었습니다. 기록의 세 규칙이 모두 사실일 때, 반드시 맞는 말은 무엇일까요?',
  'options': ['황금 인장이 있으면 초대권이 있다', '민트 향이면 초대권이 있다', '민트 향이 없으면 초대권도 없다', '리본이 있으면 황금 인장도 있다'],
  'answer': 2,
  'image': 'quiz-count-candy.svg'},
 {'group': 'chocolate',
  'question': '두 문지기 중 한 명은 항상 참말, 다른 한 명은 항상 거짓말을 합니다. 어느 쪽인지 모르는 당신이 아래 질문을 하자 “왼쪽”이라는 답이 돌아왔습니다. 초대장이 있는 '
              '문은?',
  'options': ['왼쪽 문', '오른쪽 문', '두 문 모두', '판단할 수 없다'],
  'answer': 1,
  'image': 'quiz-count-doors.svg'}]


def load_env():
    if ENV.exists():
        for line in ENV.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
DB = Path(os.environ.get('EVENT_DB', str(DATA / 'event_v5.db')))
DATABASE_URL = os.environ.get('DATABASE_URL','')
DB_SCHEMA = os.environ.get('DB_SCHEMA','inguin_event')
PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '8000'))
HTTPS = os.environ.get('PUBLIC_HTTPS', '0') == '1' or bool(os.environ.get('VERCEL'))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Connection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def connect():
    if DATABASE_URL:
        from postgres_store import PostgresConnection
        return PostgresConnection(DATABASE_URL,DB_SCHEMA)
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=15, isolation_level=None, factory=Connection)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    return db


def safe_asset_name(name):
    return isinstance(name, str) and (not name or
        (re.fullmatch(r'[a-z0-9][a-z0-9_-]*\.(?:png|jpg|jpeg|webp|svg)', name) is not None
         and (ASSETS / name).is_file()))


def seed_questions(db):
    for n, q in enumerate(DEFAULT_QUESTIONS):
        db.execute('''INSERT INTO questions(group_key,prompt,options,answer,image,option_images,position,accepted_answers)
                      VALUES(?,?,?,?,?,?,?,?)''', (q['group'], q['question'], json.dumps(q['options'], ensure_ascii=False),
                        q['answer'], q.get('image', ''), json.dumps(q.get('option_images', [])), n, json.dumps(q.get('accepted_answers',[]),ensure_ascii=False)))


def init_db():
    if DATABASE_URL:
        from postgres_store import initialize
        initialize(DATABASE_URL,DB_SCHEMA,seed_questions)
        return
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS questions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_key TEXT NOT NULL,
          prompt TEXT NOT NULL,
          options TEXT NOT NULL,
          answer INTEGER NOT NULL,
          image TEXT NOT NULL DEFAULT '',
          option_images TEXT NOT NULL DEFAULT '[]',
          position INTEGER NOT NULL,
          accepted_answers TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS participants (
          participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          last2 TEXT NOT NULL,
          joined_at TEXT NOT NULL,
          question_ids TEXT NOT NULL,
          revision INTEGER NOT NULL,
          completed_at TEXT,
          invite_code TEXT UNIQUE,
          checked_at TEXT,
          UNIQUE(normalized_name,last2)
        );
        CREATE INDEX IF NOT EXISTS participants_completed ON participants(completed_at);
        CREATE TABLE IF NOT EXISTS admin_sessions (
          token_hash TEXT PRIMARY KEY,
          csrf TEXT NOT NULL,
          expires INTEGER NOT NULL
        );
        ''')
        if 'accepted_answers' not in [r['name'] for r in db.execute('PRAGMA table_info(questions)')]:
            db.execute("ALTER TABLE questions ADD COLUMN accepted_answers TEXT NOT NULL DEFAULT '[]'")
        db.execute('INSERT OR IGNORE INTO config(id,revision) VALUES(1,1)')
        if 'bank_version' not in [r['name'] for r in db.execute('PRAGMA table_info(config)')]:
            db.execute('ALTER TABLE config ADD COLUMN bank_version INTEGER NOT NULL DEFAULT 5')
        if not db.execute('SELECT 1 FROM questions LIMIT 1').fetchone():
            seed_questions(db)
        bank=db.execute('SELECT bank_version FROM config WHERE id=1').fetchone()['bank_version']
        if bank<6:
            prompts=[r['prompt'] for r in db.execute('SELECT prompt FROM questions ORDER BY position,id')]
            if prompts==LEGACY_V5_PROMPTS:
                db.execute('BEGIN IMMEDIATE')
                try:
                    db.execute('DELETE FROM questions');seed_questions(db)
                    db.execute('UPDATE config SET revision=revision+1 WHERE id=1')
                    db.commit()
                except Exception:db.rollback();raise
            db.execute('UPDATE config SET bank_version=6 WHERE id=1')


def setup():
    global PASSWORD
    DATA.mkdir(parents=True, exist_ok=True)
    if not ENV.exists():
        PASSWORD = secrets.token_urlsafe(22)
        ENV.write_text(f'ADMIN_PASSWORD={PASSWORD}\nHOST=0.0.0.0\nPORT=8000\nPUBLIC_HTTPS=0\n', encoding='utf-8')
        try: ENV.chmod(0o600)
        except OSError: pass
        print('\n관리자 비밀번호: ' + PASSWORD + '\n.env에 저장했습니다. GitHub에 업로드하지 마세요.\n')
    elif not PASSWORD:
        raise RuntimeError('.env 파일에 ADMIN_PASSWORD가 없습니다.')
    init_db()
    print('설정 완료: http://localhost:8000/ (관리자: /admin)')
    print('기존 운영 기록을 옮길 때는 README의 버전 이전 안내를 확인하세요.')


def normalize_name(name):
    if not isinstance(name, str): return None
    display = ' '.join(unicodedata.normalize('NFC', name).strip().split())
    if not 2 <= len(display) <= 30 or not re.fullmatch(r'[가-힣A-Za-z .\-]{2,30}', display):
        return None
    return display, display.casefold()


def validate_person(name, last2):
    person = normalize_name(name)
    if not person or not isinstance(last2, str) or re.fullmatch(r'\d{2}', last2) is None:
        return None
    return person


def question_public(row):
    return {'id': row['id'], 'group': row['group_key'], 'question': row['prompt'],
            'options': json.loads(row['options']), 'image': row['image'],
            'option_images': json.loads(row['option_images']), 'kind': 'text' if json.loads(row['accepted_answers']) else 'choice'}


def participant_public(row):
    return {'status': 'completed', 'name': row['name'], 'last2': row['last2'],
            'invite_code': row['invite_code'], 'completed_at': row['completed_at'],
            'checked': bool(row['checked_at'])}


def select_questions(db):
    selected = []
    for group in QUIZ_GROUPS:
        rows = db.execute('SELECT id FROM questions WHERE group_key=? ORDER BY position,id', (group,)).fetchall()
        if not rows: raise ValueError(f'문제 은행에 {GROUP_LABELS[group]} 유형의 문제가 없습니다.')
        selected.append(rows[secrets.randbelow(len(rows))]['id'])
    return selected


def start_participant(name, last2):
    person = validate_person(name, last2)
    if not person: return 400, {'error': '이름과 학번 끝 두 자리(숫자 2개)를 입력해 주세요.'}
    display, normalized = person
    with connect() as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            rev = db.execute('SELECT revision FROM config WHERE id=1').fetchone()['revision']
            row = db.execute('SELECT * FROM participants WHERE normalized_name=? AND last2=?', (normalized, last2)).fetchone()
            if row and row['completed_at']:
                db.commit(); return 200, participant_public(row)
            if not row or row['revision'] != rev:
                try: ids = select_questions(db)
                except ValueError as e: db.rollback(); return 503, {'error': str(e)}
                if row:
                    db.execute('UPDATE participants SET name=?,question_ids=?,revision=? WHERE participant_id=?',
                               (display,json.dumps(ids),rev,row['participant_id']))
                else:
                    db.execute('''INSERT INTO participants(name,normalized_name,last2,joined_at,question_ids,revision)
                                  VALUES(?,?,?,?,?,?)''', (display,normalized,last2,now(),json.dumps(ids),rev))
                row = db.execute('SELECT * FROM participants WHERE normalized_name=? AND last2=?', (normalized,last2)).fetchone()
            ids = json.loads(row['question_ids'])
            questions = {r['id']: r for r in db.execute('SELECT * FROM questions')}
            if any(i not in questions for i in ids):
                db.rollback(); return 409, {'error': '문제가 변경되었습니다. 다시 시작해 주세요.'}
            db.commit()
            return 200, {'status': 'quiz', 'questions': [question_public(questions[i]) for i in ids]}
        except Exception:
            db.rollback(); raise


def normalize_answer(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).casefold()


def answer_matches(question, answer):
    accepted = json.loads(question['accepted_answers'])
    if accepted:
        return isinstance(answer,str) and normalize_answer(answer) in [normalize_answer(x) for x in accepted]
    return type(answer) is int and question['answer'] == answer


def submit_quiz(name, last2, answers):
    person = validate_person(name, last2)
    if not person: return 400, {'error': '이름 또는 학번 끝 두 자리가 올바르지 않습니다.'}
    if not isinstance(answers,list) or len(answers)!=QUIZ_LENGTH or any(type(a) not in (int,str) or (isinstance(a,str) and not 1<=len(a.strip())<=100) for a in answers):
        return 400, {'error': '세 문제의 답을 모두 입력하거나 선택해 주세요.'}
    _, normalized = person
    with connect() as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM participants WHERE normalized_name=? AND last2=?', (normalized,last2)).fetchone()
            if not row: db.rollback(); return 404, {'error': '먼저 이름과 학번 끝 두 자리를 입력해 주세요.'}
            if row['completed_at']: db.commit(); return 200, participant_public(row)
            rev = db.execute('SELECT revision FROM config WHERE id=1').fetchone()['revision']
            if row['revision'] != rev: db.rollback(); return 409, {'error': '문제가 변경되었습니다. 처음부터 다시 시작해 주세요.'}
            ids = json.loads(row['question_ids'])
            qs = {r['id']: r for r in db.execute('SELECT * FROM questions')}
            if any(i not in qs for i in ids): db.rollback(); return 409, {'error': '퀴즈가 갱신되었습니다. 다시 시작해 주세요.'}
            missed = [n for n,(id,a) in enumerate(zip(ids,answers)) if not answer_matches(qs[id], a)]
            if missed:
                db.commit(); return 200, {'status':'retry', 'missed':missed,
                    'error':'아쉬워요! 표시된 문제를 다시 풀고 초대장을 받아보세요.'}
            invite_code = 'INJ-' + secrets.token_hex(8).upper()
            db.execute('UPDATE participants SET completed_at=?,invite_code=? WHERE participant_id=? AND completed_at IS NULL',
                       (now(), invite_code, row['participant_id']))
            result = db.execute('SELECT * FROM participants WHERE participant_id=?', (row['participant_id'],)).fetchone()
            db.commit(); return 200, participant_public(result)
        except Exception:
            db.rollback(); raise


def session_hash(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def get_admin(cookie_header):
    try:
        cookies=SimpleCookie();cookies.load(cookie_header or '')
        token=cookies['event_admin'].value
    except (ValueError,KeyError): return None
    if re.fullmatch(r'[0-9a-f]{64}',token) is None:return None
    with connect() as db:
        return db.execute('SELECT token_hash,csrf,expires FROM admin_sessions WHERE token_hash=? AND expires>?',
                          (session_hash(token),int(time.time()))).fetchone()


def login_allowed(ip):
    if DATABASE_URL:
        with connect() as db:
            count=db.execute('SELECT count(*) AS n FROM login_failures WHERE ip=? AND failed_at>?',(ip,int(time.time())-300)).fetchone()['n']
        return count<8
    with FAIL_LOCK:
        recent=[t for t in LOGIN_FAILURES.get(ip,[]) if time.monotonic()-t < 300]
        LOGIN_FAILURES[ip]=recent
        return len(recent)<8


def login_failed(ip):
    if DATABASE_URL:
        with connect() as db:
            db.execute('DELETE FROM login_failures WHERE failed_at<?',(int(time.time())-300,))
            db.execute('INSERT INTO login_failures(ip,failed_at) VALUES(?,?)',(ip,int(time.time())))
        return
    with FAIL_LOCK: LOGIN_FAILURES.setdefault(ip,[]).append(time.monotonic())


def admin_dashboard():
    with connect() as db:
        counts = dict(db.execute('''SELECT COUNT(*) joined,
          SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) completed,
          SUM(CASE WHEN checked_at IS NOT NULL THEN 1 ELSE 0 END) checked
          FROM participants''').fetchone())
        recent = [dict(r) for r in db.execute('''SELECT name,last2,joined_at,completed_at,invite_code,checked_at
          FROM participants WHERE completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 300''')]
    for k in counts: counts[k]=counts[k] or 0
    return {'counts':counts,'recent':recent, 'config':{'quiz_length':QUIZ_LENGTH, 'unlimited':True}}


def lookup(query):
    """Find by invitation number or the exact full name and two student-number digits."""
    if not isinstance(query, str): return None
    query = ' '.join(query.strip().split())
    with connect() as db:
        if re.fullmatch(r'INJ-[A-F0-9]{16}', query.upper()):
            r = db.execute(
                'SELECT name,last2,joined_at,completed_at,invite_code,checked_at FROM participants WHERE invite_code=?',
                (query.upper(),)).fetchone()
        else:
            match = re.fullmatch(r'(.+?)\s*(\d{2})', query)
            person = validate_person(match.group(1), match.group(2)) if match else None
            if not person: return None
            r = db.execute(
                'SELECT name,last2,joined_at,completed_at,invite_code,checked_at FROM participants WHERE normalized_name=? AND last2=?',
                (person[1], match.group(2))).fetchone()
        return dict(r) if r else None


def search_participants(query):
    if not isinstance(query,str):return [],False
    query=' '.join(unicodedata.normalize('NFC',query).strip().split())
    if not query or len(query)>50:return [],False
    exact=lookup(query)
    if exact:return [exact],False
    # A typed invitation code or name+suffix is an exact lookup, never a fuzzy name search.
    if query.upper().startswith('INJ-') or re.search(r'\d',query):return [],False
    if re.fullmatch(r'[가-힣A-Za-z .\-]{1,30}',query) is None:return [],False
    with connect() as db:
        rows=[dict(r) for r in db.execute("SELECT name,last2,joined_at,completed_at,invite_code,checked_at FROM participants WHERE instr(normalized_name,?)>0 ORDER BY joined_at DESC,participant_id DESC LIMIT 51",(query.casefold(),))]
    return rows[:50],len(rows)>50


def mark_checked(invite_code):
    if not isinstance(invite_code,str) or re.fullmatch(r'INJ-[0-9A-F]{16}',invite_code) is None:
        return 400,{'error':'확인번호 형식이 올바르지 않습니다.'}
    with connect() as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT checked_at FROM participants WHERE invite_code=? AND completed_at IS NOT NULL',(invite_code,)).fetchone()
            if not r:db.rollback();return 404,{'error':'발급된 초대장이 없습니다.'}
            if r['checked_at']:db.rollback();return 409,{'error':'이미 현장 확인 처리가 완료된 초대장입니다.'}
            db.execute('UPDATE participants SET checked_at=? WHERE invite_code=?', (now(),invite_code))
            db.commit();return 200,{'ok':True,'message':'초대장 확인 완료'}
        except Exception:db.rollback();raise


def list_questions():
    with connect() as db:
        rows=db.execute('SELECT * FROM questions ORDER BY position,id').fetchall()
    return [{'group':r['group_key'], 'question':r['prompt'],'options':json.loads(r['options']),
             'answer':r['answer'],'accepted_answers':json.loads(r['accepted_answers']),'image':r['image'],'option_images':json.loads(r['option_images'])} for r in rows]


def update_questions(questions):
    if not isinstance(questions,list) or not 3<=len(questions)<=70:
        return 400,{'error':'문제는 3~70개 등록할 수 있습니다.'}
    groups=set(); clean=[]
    for i,q in enumerate(questions):
        if not isinstance(q,dict):return 400,{'error':f'{i+1}번 문제 형식이 올바르지 않습니다.'}
        group=q.get('group');prompt=q.get('question');opts=q.get('options');answer=q.get('answer')
        img=q.get('image','') or '';opt_imgs=q.get('option_images',[]) or []
        if group not in QUIZ_GROUPS:return 400,{'error':f'{i+1}번 문제 유형을 선택해 주세요.'}
        if not isinstance(prompt,str) or not 2<=len(prompt.strip())<=350:return 400,{'error':f'{i+1}번 문제 문장을 확인해 주세요.'}
        accepted=q.get('accepted_answers',[])
        if not isinstance(accepted,list) or len(accepted)>10 or any(not isinstance(x,str) or not 1<=len(x.strip())<=100 for x in accepted):
            return 400,{'error':f'{i+1}번 서술형 정답을 확인해 주세요.'}
        if not accepted and (not isinstance(opts,list) or not 2<=len(opts)<=5 or any(not isinstance(o,str) or not 1<=len(o.strip())<=100 for o in opts)):
            return 400,{'error':f'{i+1}번 보기 형식을 확인해 주세요.'}
        if not accepted and (type(answer) is not int or not 0<=answer<len(opts)):return 400,{'error':f'{i+1}번 정답 번호를 확인해 주세요.'}
        if not safe_asset_name(img):return 400,{'error':f'{i+1}번 문제의 이미지 파일이 없습니다.'}
        if not isinstance(opt_imgs,list) or (opt_imgs and (len(opt_imgs)!=len(opts) or any(not safe_asset_name(n) or not n for n in opt_imgs))):
            return 400,{'error':f'{i+1}번 보기 이미지를 확인해 주세요.'}
        if accepted:
            opts=[];answer=0;opt_imgs=[]
        groups.add(group)
        clean.append((group,prompt.strip(),json.dumps([x.strip() for x in opts],ensure_ascii=False),answer,img,
                      json.dumps(opt_imgs),i,json.dumps(accepted,ensure_ascii=False)))
    if groups != set(QUIZ_GROUPS):return 400,{'error':'이미지 속담, 티켓 찾기, 초콜릿 관찰 각 유형의 문제가 최소 1개 필요합니다.'}
    with connect() as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM questions')
            db.executemany('''INSERT INTO questions(group_key,prompt,options,answer,image,option_images,position,accepted_answers)
                              VALUES(?,?,?,?,?,?,?,?)''',clean)
            db.execute('UPDATE config SET revision=revision+1 WHERE id=1')
            db.commit();return 200,{'ok':True,'message':f'{len(clean)}개 문제를 저장했어요. 미완료 참가자는 재시작하면 새 문제를 받습니다. 발급된 초대장은 유지됩니다.'}
        except Exception:db.rollback();raise


class Handler(BaseHTTPRequestHandler):
    server_version='InjiyongEvent/6.0'
    sys_version=''
    protocol_version='HTTP/1.1'

    def log_message(self, fmt, *args):
        print(f'[{self.log_date_time_string()}] {self.client_address[0]} {fmt % args}')

    def send_data(self, status, content, mime, headers=None,cache=False):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','public, max-age=3600' if cache else 'no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        if headers:
            for k,v in headers.items():self.send_header(k,v)
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(content)

    def reply(self,status,body,headers=None):
        self.send_data(status,json.dumps(body,ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8',headers)

    def parse_body(self):
        try:
            length=int(self.headers.get('Content-Length','-1'))
            if not 0<=length<=100000:return None
            payload=json.loads(self.rfile.read(length).decode('utf-8'))
            return payload if isinstance(payload,dict) else None
        except (ValueError,UnicodeDecodeError):return None

    def require_admin(self,csrf=False):
        session=get_admin(self.headers.get('Cookie',''))
        if not session:self.reply(401,{'error':'관리자 로그인 후 이용해 주세요.'});return None
        if csrf and not hmac.compare_digest(self.headers.get('X-CSRF',''),session['csrf']):
            self.reply(403,{'error':'보안 인증 정보가 올바르지 않습니다.'});return None
        return session

    def do_GET(self):
        path=urlsplit(self.path).path
        files={'/':'index.html','/admin':'admin.html','/static/style.css':'style.css','/static/invitation.css':'invitation.css','/static/invitation.js':'invitation.js','/static/v5.css':'v5.css',
               '/static/app.js':'app.js','/static/admin.js':'admin.js','/static/landscape.svg':'landscape.svg'}
        if path.startswith('/static/fonts/'):
            name=path.rsplit('/',1)[-1]
            if re.fullmatch(r'[A-Za-z0-9-]+\.(woff2|txt)',name) and (STATIC/'fonts'/name).is_file():
                f=STATIC/'fonts'/name
                return self.send_data(200,f.read_bytes(),'font/woff2' if f.suffix=='.woff2' else 'text/plain; charset=utf-8',cache=True)
        if path in files:
            f=STATIC/files[path];mime=mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
            if f.suffix=='.js':mime='application/javascript'
            return self.send_data(200,f.read_bytes(),mime + ('; charset=utf-8' if ('text/' in mime or 'javascript' in mime) else ''),cache=False)
        if path=='/assets/landing':
            f=next((ASSETS/('landing'+ext) for ext in ('.png','.jpg','.webp') if (ASSETS/('landing'+ext)).is_file()),None)
            if f:return self.send_data(200,f.read_bytes(),mimetypes.guess_type(f.name)[0])
        if path=='/assets/mascot.png':
            f=ASSETS/'mascot.png'
            if f.is_file():return self.send_data(200,f.read_bytes(),'image/png')
        if path.startswith('/assets/quiz-') or path.startswith('/assets/ticket-'):
            name=path.split('/')[-1]
            if safe_asset_name(name):
                f=ASSETS/name
                return self.send_data(200,f.read_bytes(),mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
        if path=='/api/invite-art':
            code=parse_qs(urlsplit(self.path).query).get('code',[''])[0]
            if re.fullmatch(r'INJ-[A-F0-9]{16}',code) is None:return self.reply(403,{'error':'발급된 초대장 확인번호가 필요합니다.'})
            with connect() as db:
                exists=db.execute('SELECT 1 FROM participants WHERE invite_code=? AND completed_at IS NOT NULL',(code,)).fetchone()
            if not exists:return self.reply(403,{'error':'초대장 확인번호가 올바르지 않습니다.'})
            f=ASSETS/'wonka-injiyong-cutout.png'
            return self.send_data(200,f.read_bytes(),'image/png')
        if path=='/api/admin/state':
            session=self.require_admin()
            if session:return self.reply(200,{**admin_dashboard(),'csrf':session['csrf']})
            return
        if path=='/api/admin/questions':
            if self.require_admin():return self.reply(200,{'questions':list_questions()})
            return
        if path=='/api/admin/participants.csv':
            if not self.require_admin():return
            with connect() as db:
                rows=db.execute('SELECT name,last2,joined_at,completed_at,invite_code,checked_at FROM participants ORDER BY joined_at').fetchall()
            text=io.StringIO();text.write('\ufeff');writer=csv.writer(text)
            writer.writerow(['이름','학번 끝 2자리','참가 시작','초대장 발급','초대장 번호','현장 확인'])
            for r in rows:writer.writerow([r[k] for k in r.keys()])
            return self.send_data(200,text.getvalue().encode('utf-8'),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="invitation_v6.csv"'})
        if path=='/api/admin/qr.svg':
            if not self.require_admin():return
            url=parse_qs(urlsplit(self.path).query).get('url',[''])[0]
            parsed=urlsplit(url)
            if parsed.scheme not in ('http','https') or not parsed.netloc or len(url)>250:return self.reply(400,{'error':'올바른 접속 주소를 입력하세요.'})
            try:
                import qrcode
                import qrcode.image.svg
                qr=qrcode.QRCode(box_size=8,border=3,error_correction=qrcode.constants.ERROR_CORRECT_M)
                qr.add_data(url);qr.make(fit=True)
                return self.send_data(200,qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string(),'image/svg+xml; charset=utf-8')
            except ImportError:return self.reply(503,{'error':'qrcode 패키지가 설치되지 않았습니다.'})
        return self.reply(404,{'error':'해당 주소를 찾을 수 없습니다.'})

    def do_POST(self):
        path=urlsplit(self.path).path
        data=self.parse_body()
        if data is None:return self.reply(400,{'error':'요청 본문을 확인해 주세요.'})
        if path=='/api/start':
            return self.reply(*start_participant(data.get('name'),data.get('last2')))
        if path=='/api/quiz':
            return self.reply(*submit_quiz(data.get('name'),data.get('last2'),data.get('answers')))
        if path=='/api/admin/login':
            given=data.get('password')
            if not isinstance(given,str) or not PASSWORD or not hmac.compare_digest(given,PASSWORD):
                return self.reply(403,{'error':'비밀번호가 맞지 않습니다.'})
            token,csrf=secrets.token_hex(32),secrets.token_hex(24)
            with connect() as db:
                db.execute('DELETE FROM admin_sessions WHERE expires<?',(int(time.time()),))
                db.execute('INSERT INTO admin_sessions(token_hash,csrf,expires) VALUES(?,?,?)',
                           (session_hash(token),csrf,int(time.time())+43200))
            cookie=f'event_admin={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200'
            if HTTPS:cookie+='; Secure'
            return self.reply(200,{'ok':True,'csrf':csrf},{'Set-Cookie':cookie})
        if path=='/api/admin/logout':
            session=self.require_admin(csrf=True)
            if not session:return
            with connect() as db:db.execute('DELETE FROM admin_sessions WHERE token_hash=?',(session['token_hash'],))
            cookie='event_admin=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
            if HTTPS:cookie+='; Secure'
            return self.reply(200,{'ok':True},{'Set-Cookie':cookie})
        if path=='/api/admin/search':
            if self.require_admin(csrf=True):
                matches,truncated=search_participants(data.get('query'))
                return self.reply(200,{'participant':matches[0] if len(matches)==1 else None,'participants':matches,'truncated':truncated})
            return
        if path=='/api/admin/check':
            if not self.require_admin(csrf=True):return
            return self.reply(*mark_checked(data.get('invite_code')))
        if path=='/api/admin/questions':
            if not self.require_admin(csrf=True):return
            return self.reply(*update_questions(data.get('questions')))
        return self.reply(404,{'error':'해당 주소를 찾을 수 없습니다.'})


def main():
    if sys.argv[1:]==['setup']:setup();return
    if not DB.exists() or not PASSWORD:
        print('먼저 실행해 주세요: python app.py setup',file=sys.stderr);sys.exit(1)
    init_db()
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    server.daemon_threads=True
    print(f'행사 접속: http://localhost:{PORT}/')
    print(f'관리자: http://localhost:{PORT}/admin')
    try:server.serve_forever()
    except KeyboardInterrupt:print('\n서버 종료')
    finally:server.server_close()


if __name__=='__main__':main()
