"""LangGraph career discovery + durable multi-turn interview assessment."""
import json
import re
from pathlib import Path
from typing import TypedDict
from tools.graph_runtime import StateGraph,START,END
from tools.job_sources import (fetch_greenhouse,rank_jobs,detected_skills,DEFAULT_BOARDS)
from tools.llm import response_json
from memory.store import (load_profile,create_interview,get_interview,submit_answer,
                          assessment_history,list_weaknesses,utcnow)

ROOT=Path(__file__).resolve().parents[1]
QUESTION_BANK = [
  {'topic':'RAG','question':'Explain the RAG pipeline and how you would evaluate retrieval quality.',
   'keywords':['retrieve','embedding','vector','precision','recall'],
   'explanation':'Discuss indexing/embeddings, retrieval, context grounding, and metrics such as Recall@k.'},
  {'topic':'Python','question':'How would you design a Python REST API that handles validation, errors, and automated testing?',
   'keywords':['endpoint','validate','error','test','status'],
   'explanation':'Cover endpoints, schema validation, status codes, exception handling, and automated tests.'},
  {'topic':'SQL','question':'How would you diagnose a slow SQL query that joins several large tables?',
   'keywords':['explain','index','join','filter','plan'],
   'explanation':'Discuss EXPLAIN plans, indexes, join strategies, filters, and measurements.'},
  {'topic':'Docker','question':'Describe how to containerize and deploy a Python service reliably.',
   'keywords':['dockerfile','image','dependency','environment','health'],
   'explanation':'Discuss Dockerfile, dependency installation, environment variables, health checks, and deployment.'},
  {'topic':'Machine Learning','question':'How would you check if a binary classifier generalizes and avoids data leakage?',
   'keywords':['split','train','validation','test','leakage'],
   'explanation':'Discuss train/validation/test splits, leakage prevention, relevant metrics, and error analysis.'},
  {'topic':'Testing','question':'What is the difference between unit, integration, and end-to-end testing?',
   'keywords':['unit','integration','end','mock','coverage'],
   'explanation':'Explain test levels, fixtures/mocks, integration boundaries, and the coverage tradeoff.'},
  {'topic':'AWS','question':'How could you deploy and monitor a small API using AWS cloud services?',
   'keywords':['compute','database','iam','logs','monitor'],
   'explanation':'Discuss compute, managed data storage, security/IAM, logging, and monitoring.'},
  {'topic':'Git','question':'What workflow would you use to review and safely merge a team contribution?',
   'keywords':['branch','pull','review','test','merge'],
   'explanation':'Describe feature branches, pull requests, code review, CI tests, and merge strategy.'},
]

CODING_TASKS = {
  'Python': {'topic':'Python','type':'coding',
    'question':'Coding exercise: Write a Python function count_words(text) that returns a dictionary of lowercase word frequencies. Ignore punctuation and handle empty input. Explain your approach.',
    'keywords':['def','lower','split','dict','return'],
    'explanation':'A good solution normalizes text, tokenizes words, counts frequencies, handles punctuation and the empty string, and returns a dictionary. Do not execute untrusted submissions.'},
  'SQL': {'topic':'SQL','type':'coding',
    'question':'Coding exercise: Write SQL that returns the customer_id and order count for customers with at least two orders from an orders(customer_id, order_id) table.',
    'keywords':['select','count','group by','having','from'],
    'explanation':'Use SELECT customer_id, COUNT(*), FROM orders, GROUP BY customer_id, HAVING COUNT(*) >= 2.'}
}


class JobState(TypedDict,total=False):
    mode:str
    boards:list
    profile:dict
    jobs:list
    ranked_jobs:list
    errors:list

def load_node(s):return {'profile':load_profile()}
def search_node(s):
    if s.get('mode')=='demo':
        jobs=json.loads((ROOT/'examples'/'sample_jobs.json').read_text(encoding='utf-8'))
        return {'jobs':jobs,'errors':[]}
    jobs,errors=fetch_greenhouse(s.get('boards',DEFAULT_BOARDS))
    return {'jobs':jobs,'errors':errors}
def filter_node(s):return {'ranked_jobs':rank_jobs(s['jobs'],s['profile'])}

def build_job_graph():
    g=StateGraph(JobState)
    for k,f in [('load',load_node),('search',search_node),('match',filter_node)]:g.add_node(k,f)
    g.add_edge(START,'load');g.add_edge('load','search');g.add_edge('search','match');g.add_edge('match',END)
    return g.compile()

def find_jobs(mode='demo',boards=None):
    if mode not in ('demo','live'):raise ValueError('Invalid mode')
    result=build_job_graph().invoke({'mode':mode,'boards':boards or DEFAULT_BOARDS})
    return {'jobs':result['ranked_jobs'],'errors':result['errors'],'mode':mode,'fetched':len(result['jobs'])}

def choose_questions(job,profile=None):
    if job.get('mode')=='venture':
        return [
          {'topic':'Market Validation','type':'venture coaching',
           'question':'Who is your first paying customer, and what evidence would demonstrate that the customer has this problem?',
           'keywords':['customer','interview','pilot','problem','evidence'],
           'explanation':'Describe a narrowly defined customer, problem interviews, pilot hypothesis, and measurable signals.'},
          {'topic':'MVP Design','type':'venture coaching',
           'question':'What is the smallest MVP you would build, and what metrics and safeguards would you use to judge its success?',
           'keywords':['mvp','prototype','metric','feedback','privacy'],
           'explanation':'Choose an MVP scope, success metric, user feedback loop, and a privacy or safety safeguard.'},
          dict(CODING_TASKS['Python'])]
    profile=profile or load_profile()
    text=(job.get('title','')+' '+job.get('description','')).lower()
    user_skills=[s.lower() for s in profile.get('skills',[])]
    gaps={w['topic'] for w in list_weaknesses()}
    scored=[]
    for q in QUESTION_BANK:
        topic=q['topic'].lower()
        relevance=3 if topic in text else 0
        if topic=='rag' and ('retrieval' in text or 'llm' in text):relevance+=3
        if topic=='docker' and 'container' in text:relevance+=2
        if topic=='python' and 'backend' in text:relevance+=2
        if topic in gaps:relevance+=4
        if topic not in user_skills:relevance+=1
        scored.append((relevance,q))
    scored.sort(key=lambda p:p[0],reverse=True)
    chosen=[dict(q, type='technical') for _,q in scored[:2]]
    language='SQL' if 'sql' in text and 'python' not in text else 'Python'
    return chosen+[dict(CODING_TASKS[language])]

def start_interview(job):
    if not job or not job.get('title'):raise ValueError('A job title is required')
    questions=choose_questions(job)
    return get_interview(create_interview(job,questions))

def _keyword_found(k, text):
    aliases = {
        'retrieve':['retrieve','retrieval','retrieving'], 'embedding':['embedding','embeddings','embed'],
        'vector':['vector','vectors'],
        'split':['split','findall','tokenize'], 'dict':['dict','{}','counter('],
        'health':['health','readiness'], 'test':['test','pytest'],
        'error':['error','exception'], 'validate':['validate','validation'],
    }
    if k=='end':return bool(re.search(r'\bend.to.end\b|\be2e\b',text))
    return any(bool(re.search(r'(?<!\w)'+re.escape(x)+r'(?!\w)',text)) if x.isalnum() else x in text
               for x in aliases.get(k,[k]))

def deterministic_grade(question,answer):
    """Transparent keyword rubric for demo; not equivalent to human assessment."""
    norm=answer.lower()
    keywords=question['keywords']
    hits=[k for k in keywords if _keyword_found(k,norm)]
    missing=[k for k in keywords if k not in hits]
    detail_bonus=10 if len(answer.split())>=35 else 0
    score=min(100,round(90*len(hits)/len(keywords)+detail_bonus))
    return {'score':score,'strengths':f'Mentioned {", ".join(hits)}.' if hits else 'Attempted the question.',
            'missing':missing, 'feedback':question['explanation'],
            'method':'demo keyword rubric','limitations':'Keyword presence does not prove conceptual correctness.'}

def ai_grade(question,answer,job):
    instructions=('You are a fair technical-interview evaluator. Evaluate only the actual candidate answer, '
     'not presumed experience. Output JSON: score (integer 0-100), strengths (short string), '
     'missing (array of 1-4 technical concepts), feedback (specific suggestions). '
     'Penalize incorrect explanations even if keywords are present. Avoid inventing details. '
     'A short but accurate answer can score well. The expected answer guidance is not proof of candidate correctness.')
    request={'question':question['question'],'topic':question['topic'],'expected':question['explanation'],
             'candidate_answer':answer[:5000],'job_title':job['title']}
    raw=response_json(instructions,json.dumps(request))
    score=int(raw['score'])
    if not 0<=score<=100:raise ValueError('Invalid score')
    missing=raw.get('missing',[])
    return {'score':score,'strengths':str(raw.get('strengths',''))[:500],
            'missing':[str(x)[:70] for x in missing[:5]] if isinstance(missing,list) else [],
            'feedback':str(raw.get('feedback',''))[:800],'method':'AI rubric'}

class AnswerState(TypedDict,total=False):
    interview_id:str
    answer:str
    use_ai:bool
    interview:dict
    question:dict
    grade:dict
    updated:dict
    report:dict

def check_node(s):
    interview=get_interview(s['interview_id'])
    if not interview or interview['finished']:raise ValueError('Interview missing or finished')
    answer=s['answer'].strip()
    if not answer:raise ValueError('Answer cannot be empty')
    if len(answer)>5000:raise ValueError('Answer must be 5000 characters or less')
    return {'interview':interview,'question':interview['questions'][interview['current_index']]}
def evaluate_node(s):
    question=s['question'];result=None
    if s.get('use_ai'):
        try:result=ai_grade(question,s['answer'],s['interview']['job'])
        except Exception as exc:
            result=deterministic_grade(question,s['answer'])
            result['warning']=f'AI scoring unavailable ({type(exc).__name__}); keyword rubric used.'
    else:result=deterministic_grade(question,s['answer'])
    return {'grade':result}
def save_node(s):
    return {'updated':submit_answer(s['interview_id'],s['answer'],s['grade'])}
def report_node(s):
    iv=s['updated']
    scores=[r['result']['score'] for r in iv['responses']]
    return {'report':{'interview_id':iv['id'],'job_title':iv['job']['title'],
          'questions_completed':len(scores),'total_questions':len(iv['questions']),
          'average_score':round(sum(scores)/len(scores),1),'complete':bool(iv['finished']),
          'answers':iv['responses'],'improvement_topics':list(dict.fromkeys(r['topic'] for r in iv['responses'] if r['result']['score']<70)),
          'next_steps':['Read an article about your lowest-scoring skill','Review the feedback and refine your answer','Repeat the assessment and compare scores']}}

def build_answer_graph():
    g=StateGraph(AnswerState)
    for name,fun in [('validate',check_node),('evaluate',evaluate_node),('persist',save_node),('report',report_node)]:g.add_node(name,fun)
    g.add_edge(START,'validate');g.add_edge('validate','evaluate');g.add_edge('evaluate','persist');g.add_edge('persist','report');g.add_edge('report',END)
    return g.compile()

def answer_question(interview_id,answer,use_ai=False):
    return build_answer_graph().invoke({'interview_id':interview_id,'answer':answer,'use_ai':use_ai})['report']

def manual_job(title,description,company='User-provided job description'):
    return {'id':'manual','company':company,'title':title,'location':'Not specified',
            'description':description,'url':'','mode':'user-provided',
            'source':'User-provided description (not independently verified)'}
