"""LangGraph: memory -> fetch -> rank -> explain -> save."""
import json
from pathlib import Path
from typing import TypedDict
from tools.graph_runtime import StateGraph,START,END
from tools.article_sources import fetch_articles,best_articles
from tools.llm import summarize_article
from memory.store import (load_profile,list_weaknesses,read_urls,store_brief,utcnow)

ROOT=Path(__file__).resolve().parents[1]
class DailyState(TypedDict,total=False):
    mode:str
    use_ai:bool
    profile:dict
    weaknesses:list
    already_read:set
    candidates:list
    selected:list
    brief:dict
    feed_errors:list
    brief_id:str

def context_node(s):
    return {'profile':load_profile(),'weaknesses':list_weaknesses(),'already_read':read_urls()}

def discover_node(s):
    if s.get('mode','demo')=='demo':
        articles=json.loads((ROOT/'examples'/'sample_articles.json').read_text(encoding='utf-8'))
        errors=[]
    else:
        articles,errors=fetch_articles()
    return {'candidates':articles,'feed_errors':errors}

def rank_node(s):
    return {'selected':best_articles(s['candidates'],s['profile'],s['weaknesses'],s['already_read'])}

def summarize_node(s):
    items=[]
    for a in s['selected']:
        info=summarize_article(a,s['profile'],bool(s.get('use_ai',False) and s.get('mode')=='live'))
        items.append({**a,**info,'reading_minutes':6})
    return {'brief':{'created_at':utcnow(),'mode':s.get('mode','demo'),
            'articles':items,'planned_reading_minutes':len(items)*6,
            'status':'complete' if len(items)==3 else 'partial',
            'warnings':s.get('feed_errors',[]),
            'note':('DEMO: cached, historical examples. Not a live daily feed.' if s.get('mode')=='demo'
                    else 'Live RSS results. AI summaries, if enabled, are limited to the retrieved excerpts.') }}

def persist_node(s):
    return {'brief_id':store_brief(s['brief'])}

def build_agent():
    g=StateGraph(DailyState)
    for k,fn in [('load_context',context_node),('discover',discover_node),
                 ('rank',rank_node),('summarize',summarize_node),('persist',persist_node)]:g.add_node(k,fn)
    g.add_edge(START,'load_context')
    g.add_edge('load_context','discover')
    g.add_edge('discover','rank')
    g.add_edge('rank','summarize')
    g.add_edge('summarize','persist')
    g.add_edge('persist',END)
    return g.compile()

def run_daily(mode='demo',use_ai=False):
    if mode not in ('demo','live'):raise ValueError('mode must be demo or live')
    return build_agent().invoke({'mode':mode,'use_ai':use_ai})['brief']
