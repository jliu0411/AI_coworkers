import json
import pytest
from pathlib import Path
from agents.daily_tech_agent import run_daily
from agents.career_coach_agent import find_jobs,start_interview,answer_question,manual_job
from memory import store
from evaluation.metrics import evaluate_daily,labeled_relevance_precision
from tools.article_sources import parse_feed,article_score,best_articles
from tools.job_sources import detected_skills,rank_jobs

@pytest.fixture(autouse=True)
def isolated_database(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'test.sqlite3')
    store.init_db()

def test_demo_daily_exactly_three_and_real_metadata():
    brief=run_daily('demo')
    assert brief['status']=='complete'
    metrics=evaluate_daily(brief)
    assert metrics['exactly_three']
    assert metrics['distinct_url_rate']==1.0
    assert metrics['metadata_completeness']==1.0
    assert all(a['url'].startswith('https://') for a in brief['articles'])
    assert store.dashboard_stats()['briefs']==1

def test_feed_parser_real_rss_date():
    xml=b'''<rss><channel><item><title>Agent Engineering</title><link>https://example.org/post</link><pubDate>Mon, 26 Oct 2026 12:00:00 GMT</pubDate><description>Useful retrieval article</description></item></channel></rss>'''
    parsed=parse_feed(xml,'Test Feed')
    assert parsed[0]['published']=='2026-10-26'
    assert parsed[0]['url']=='https://example.org/post'

def test_job_matching_and_synthetic_label():
    res=find_jobs('demo')
    assert len(res['jobs'])==3
    assert all(j['source']=='Synthetic fixture' for j in res['jobs'])
    assert all(0<=j['match']['score']<=100 for j in res['jobs'])

def test_live_fewer_than_three_does_not_fabricate(monkeypatch):
    monkeypatch.setattr('agents.daily_tech_agent.fetch_articles',lambda: ([],['offline']))
    brief=run_daily('live')
    assert brief['status']=='partial' and brief['articles']==[]

def test_interview_saved_and_followup_adapts():
    job=manual_job('Junior AI Engineer','Python FastAPI RAG and SQL technical work on model retrieval and backend integration.')
    interview=start_interview(job)
    assert len(interview['questions'])==3
    assert interview['questions'][-1]['type']=='coding'
    first_topic=interview['questions'][0]['topic']
    report=answer_question(interview['id'],'I am not sure.')
    assert report['questions_completed']==1
    updated=store.get_interview(interview['id'])
    assert updated['current_index']==1
    assert updated['questions'][1]['type']=='adaptive follow-up'
    assert updated['questions'][1]['topic']==first_topic
    assert store.list_weaknesses()[0]['topic']==first_topic.lower()
    answer_question(interview['id'],'I would explain the missing concepts using test cases.')
    report=answer_question(interview['id'],'def count_words(text): return {}')
    assert report['complete']
    assert store.dashboard_stats()['interviews_completed']==1
    assert store.dashboard_stats()['questions_answered']==3

def test_weakness_influences_future_article_score():
    a={'title':'RAG metrics explained','excerpt':'retrieval quality','published':'2026-10-20','url':'https://x.test/1'}
    profile={'interests':['Python'],'target_roles':['Backend Engineer']}
    from datetime import date
    before=article_score(a,profile,[],set(),now=date(2026,10,29))
    after=article_score(a,profile,[{'topic':'rag','weight':2}],set(),now=date(2026,10,29))
    assert after>before

def test_precision_at_3():
    assert labeled_relevance_precision([1,1,0])==pytest.approx(2/3,abs=0.001)

def test_venture_ideas_and_founder_coaching():
    from tools.venture_ideas import propose_ideas,venture_coaching_case
    ideas=propose_ideas(store.load_profile())
    assert len(ideas)==3
    assert all('validate' in idea and 'risk' in idea for idea in ideas)
    iv=start_interview(venture_coaching_case(ideas[0]))
    assert iv['questions'][0]['topic']=='Market Validation'
    assert iv['questions'][2]['type']=='coding'

def test_job_category():
    from tools.job_sources import job_category
    assert job_category('Research Intern')=='Internship'
    assert job_category('Research Scientist')=='Research'
    assert job_category('Backend Engineer')=='Job'
