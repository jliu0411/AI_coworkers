"""SQLite long-term learning, skills, saved briefs, and interview history."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv('AGENT_DB_PATH', str(ROOT / 'outputs' / 'coworkers.sqlite3')))
DEFAULT_PROFILE = {
    'name': 'Student',
    'interests': ['AI agents', 'RAG', 'Python', 'backend development', 'cloud computing'],
    'skills': ['Python', 'SQL', 'FastAPI', 'Git', 'machine learning'],
    'target_roles': ['Software Engineer', 'AI Engineer', 'Data Engineer', 'QA Engineer'],
    'preferred_location': 'California or Remote',
}

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript('''
          CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id=1), json TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS briefs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, mode TEXT, content TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS read_articles (url TEXT PRIMARY KEY, read_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS weaknesses (topic TEXT PRIMARY KEY, weight INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS interviews (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, job TEXT NOT NULL, current_index INTEGER NOT NULL, questions TEXT NOT NULL, responses TEXT NOT NULL, finished INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, interview_id TEXT, created_at TEXT NOT NULL, topic TEXT NOT NULL, score REAL NOT NULL, mode TEXT NOT NULL);
        ''')
        con.execute('INSERT OR IGNORE INTO profile(id,json) VALUES(1,?)', (json.dumps(DEFAULT_PROFILE),))

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def load_profile():
    init_db()
    with connect() as con:
        return json.loads(con.execute('SELECT json FROM profile WHERE id=1').fetchone()['json'])

def save_profile(profile):
    init_db()
    with connect() as con:
        con.execute('UPDATE profile SET json=? WHERE id=1', (json.dumps(profile),))

def store_brief(brief):
    init_db()
    brief_id = str(uuid4())
    with connect() as con:
        con.execute('INSERT INTO briefs VALUES(?,?,?,?)', (brief_id, utcnow(), brief.get('mode',''), json.dumps(brief)))
    return brief_id

def list_briefs(limit=10):
    init_db()
    with connect() as con:
        return [json.loads(r['content']) for r in con.execute('SELECT content FROM briefs ORDER BY created_at DESC LIMIT ?', (limit,))]

def mark_read(url):
    init_db()
    with connect() as con:
        con.execute('INSERT OR REPLACE INTO read_articles VALUES(?,?)', (url, utcnow()))

def read_urls():
    init_db()
    with connect() as con:
        return {r['url'] for r in con.execute('SELECT url FROM read_articles')}

def add_weakness(topic):
    init_db()
    topic = topic.strip().lower()
    if not topic: return
    with connect() as con:
        con.execute('''INSERT INTO weaknesses(topic,weight,updated_at) VALUES(?,1,?)
                       ON CONFLICT(topic) DO UPDATE SET weight=min(weight+1,5), updated_at=excluded.updated_at''',
                       (topic, utcnow()))

def list_weaknesses():
    init_db()
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT * FROM weaknesses ORDER BY weight DESC, updated_at DESC')]

def create_interview(job, questions):
    init_db()
    interview_id = str(uuid4())
    with connect() as con:
        con.execute('INSERT INTO interviews VALUES(?,?,?,?,?,?,?)',
                    (interview_id, utcnow(), json.dumps(job), 0, json.dumps(questions), '[]', 0))
    return interview_id

def get_interview(interview_id):
    init_db()
    with connect() as con:
        r = con.execute('SELECT * FROM interviews WHERE id=?',(interview_id,)).fetchone()
    if not r: return None
    d = dict(r)
    for key in ('job','questions','responses'):
        d[key] = json.loads(d[key])
    return d

def submit_answer(interview_id, answer, result):
    """Atomically store a response and advance exactly one question."""
    init_db()
    with connect() as con:
        r = con.execute('SELECT * FROM interviews WHERE id=?', (interview_id,)).fetchone()
        if not r or r['finished']:
            raise ValueError('Interview not found or already finished')
        questions = json.loads(r['questions'])
        idx = r['current_index']
        if idx >= len(questions):
            raise ValueError('No more questions')
        responses = json.loads(r['responses'])
        responses.append({'question': questions[idx]['question'], 'topic':questions[idx]['topic'], 'answer':answer,'result':result})
        finished = int(idx+1 >= len(questions))
        # Adaptive challenge: on a weak conceptual answer, replace the NEXT question
        # with a targeted follow-up; preserve the last coding exercise.
        if not finished and result['score'] < 70 and idx+1 < len(questions)-1:
            missing = [str(x) for x in result.get('missing',[]) if str(x).strip()][:4]
            if missing:
                original = questions[idx]
                questions[idx+1] = {
                    'topic': original['topic'], 'type':'adaptive follow-up',
                    'question': f"Follow-up challenge: Your previous answer missed {', '.join(missing)}. Explain these concepts and show how they apply to: {original['question']}",
                    'keywords': missing,
                    'explanation': original['explanation']}
        con.execute('UPDATE interviews SET responses=?,questions=?,current_index=?,finished=? WHERE id=?',
                    (json.dumps(responses),json.dumps(questions),idx+1,finished,interview_id))
        con.execute('INSERT INTO assessments(interview_id,created_at,topic,score,mode) VALUES(?,?,?,?,?)',
                    (interview_id,utcnow(),questions[idx]['topic'],float(result['score']),result.get('method','unknown')))
    if result['score'] < 70:
        add_weakness(questions[idx]['topic'])
    return get_interview(interview_id)

def assessment_history():
    init_db()
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT created_at,topic,score,mode FROM assessments ORDER BY id')]

def dashboard_stats():
    init_db()
    with connect() as con:
        return {
            'briefs': con.execute('SELECT count(*) FROM briefs').fetchone()[0],
            'articles_read': con.execute('SELECT count(*) FROM read_articles').fetchone()[0],
            'interviews_completed': con.execute('SELECT count(*) FROM interviews WHERE finished=1').fetchone()[0],
            'questions_answered': con.execute('SELECT count(*) FROM assessments').fetchone()[0],
        }
