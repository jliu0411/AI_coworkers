"""Measured checks, NOT claims of actual model accuracy without labeled test cases."""
from urllib.parse import urlparse
from datetime import datetime

def evaluate_daily(brief,preferences=None):
    rows=brief.get('articles',[])
    urls=[a.get('url','') for a in rows]
    valid=[u for u in urls if urlparse(u).scheme in ('http','https') and bool(urlparse(u).netloc)]
    metadata=[a for a in rows if a.get('title') and a.get('source') and a.get('published') and a.get('url')]
    return {
        'article_count':len(rows),
        'exactly_three':len(rows)==3,
        'distinct_url_rate':round(len(set(urls))/len(urls),3) if urls else 0,
        'url_format_rate':round(len(valid)/len(rows),3) if rows else 0,
        'metadata_completeness':round(len(metadata)/len(rows),3) if rows else 0,
        'source_url_reachability':'Not measured; online HTTP checks require live networking',
        'factual_summary_accuracy':'Not measured; requires manual review against full articles'
    }

def evaluate_interview(report):
    answers=report.get('answers',[])
    return {
        'questions_answered':len(answers),
        'complete':report.get('complete',False),
        'average_score':report.get('average_score',None),
        'scoring_methods':sorted({x['result']['method'] for x in answers}),
        'grading_accuracy':'Not measured; needs human-labeled assessment answers',
        'scoring_caveat':'Demo keyword scores measure term coverage, not correctness.'
    }

def labeled_relevance_precision(relevance_labels, top_k=3):
    """Given human-reviewed 0/1 relevance labels in ranked order, compute Precision@k."""
    if not relevance_labels:return None
    chosen=relevance_labels[:top_k]
    return round(sum(bool(x) for x in chosen)/len(chosen),3)
