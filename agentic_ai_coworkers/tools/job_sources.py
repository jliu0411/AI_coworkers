"""Public Greenhouse boards; no fabricated opportunities in Live mode."""
import html
import re
import requests
from urllib.parse import quote

DEFAULT_BOARDS = ['anthropic','databricks','figma','cloudflare']
SKILL_VOCAB = ['Python','SQL','Java','JavaScript','TypeScript','React','FastAPI','Docker','AWS','Azure',
               'GCP','Kubernetes','Git','Linux','Machine Learning','RAG','LLM','PyTorch',
               'TensorFlow','CI/CD','Testing','REST','C++','Go','Data Engineering','PostgreSQL']

def strip_html(raw):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',raw or ''))).strip()

def detected_skills(text):
    text = (text or '').lower()
    found=[]
    for skill in SKILL_VOCAB:
        pattern=r'(?<!\w)'+re.escape(skill.lower())+r'(?!\w)'
        if re.search(pattern,text):found.append(skill)
    return found

def fetch_greenhouse(boards,timeout=8):
    jobs,errors=[],[]
    for board in boards[:8]:
        board=board.strip().lower()
        if not re.fullmatch('[a-z0-9_-]{2,80}',board):
            errors.append(f'Invalid board token: {board[:50]}');continue
        url=f'https://boards-api.greenhouse.io/v1/boards/{quote(board)}/jobs'
        try:
            r=requests.get(url,params={'content':'true'},timeout=timeout,
                           headers={'User-Agent':'SJSU-CareerCoach/1.0 (educational job listing reader)'})
            r.raise_for_status()
            for raw in r.json().get('jobs',[]):
                desc=strip_html(raw.get('content',''))
                external_url=raw.get('absolute_url') or ''
                if not external_url.startswith('https://'):continue
                jobs.append({'id':f"{board}-{raw.get('id')}", 'company':board.title(),
                   'title':raw.get('title',''), 'location':raw.get('location',{}).get('name','Not specified'),
                   'url':external_url,'description':desc[:12000],
                   'source':'Greenhouse public job board','mode':'live'})
        except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
            errors.append(f'{board}: {type(exc).__name__}')
    ids=set();out=[]
    for job in jobs:
        if job['id'] not in ids: out.append(job);ids.add(job['id'])
    return out,errors

def evaluate_match(job, profile):
    """Explainable heuristic: not a hiring probability or qualification certification."""
    roles=profile.get('target_roles',[])
    skills=set(s.lower() for s in profile.get('skills',[]))
    required=detected_skills(job.get('description',''))
    matched=[s for s in required if s.lower() in skills]
    missing=[s for s in required if s.lower() not in skills]
    title=job.get('title','').lower()
    title_terms=set(re.findall(r'[a-z]+',' '.join(roles).lower()))-{'engineer','developer','level','entry'}
    role_alignment=bool(title_terms.intersection(re.findall(r'[a-z]+',title)))
    entry=bool(re.search(r'new grad|early career|entry.level|junior|associate|graduate',title))
    senior=bool(re.search(r'\bsenior\b|\bstaff\b|principal|director|manager|lead engineer',title))
    loc=(job.get('location','') or '').lower()
    pref=(profile.get('preferred_location','') or '').lower()
    location_match=('remote' in loc and 'remote' in pref) or ('california' in pref and bool(re.search(r'california|san francisco|san jose|palo alto|mountain view|bay area',loc)))
    coverage=len(matched)/len(required) if required else 0
    score=round(max(0,min(100,(25 if role_alignment else 0)+(20 if entry else 0)+(35*coverage)+(10 if location_match else 0)+10-(35 if senior else 0))))
    return {'score':score,'matched_skills':matched,'missing_skills':missing[:10],
            'skills_detected':len(required),'entry_signal':entry,'senior_signal':senior,
            'role_aligned':role_alignment,'location_match':location_match,
            'note':'Heuristic ranking only; validate experience, eligibility, and job requirements manually.'}

def job_category(title):
    title=(title or '').lower()
    if 'intern' in title or 'co-op' in title:return 'Internship'
    if 'research' in title:return 'Research'
    return 'Job'

def rank_jobs(jobs,profile,limit=5):
    ranked=[dict(j,match=evaluate_match(j,profile),category=job_category(j.get('title',''))) for j in jobs]
    return sorted(ranked,key=lambda j:j['match']['score'],reverse=True)[:limit]
