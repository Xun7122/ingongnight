"""Copy an existing v4 SQLite database into v5; never modify the original."""
import argparse
import sqlite3
from pathlib import Path
import app
from contextlib import closing

def main():
    parser=argparse.ArgumentParser(description='v4 참가 기록을 복사하고 v5 문제 은행으로 전환합니다.')
    parser.add_argument('source',type=Path,help='v4 data/event_v4.db 경로')
    args=parser.parse_args()
    source=args.source.resolve();target=(app.BASE/'data/event_v5.db').resolve()
    if not source.is_file():parser.error('원본 DB 파일이 없습니다.')
    if target.exists():parser.error('v5 DB가 이미 있습니다. 덮어쓰지 않습니다. 새 압축 해제 폴더에서 실행해 주세요.')
    target.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
        with closing(sqlite3.connect(target)) as dst:src.backup(dst)
    app.DB=target;app.init_db()
    status,result=app.update_questions(app.DEFAULT_QUESTIONS)
    if status!=200:raise RuntimeError(result)
    with app.connect() as db:db.execute('DELETE FROM admin_sessions')
    print('복사 완료. 기존 초대장 번호와 현장 확인 기록은 유지됩니다.')
    print('미완료 참가자는 다시 시작하면 v5 문제를 받습니다. 원본 DB는 변경하지 않았습니다.')

if __name__=='__main__':main()
