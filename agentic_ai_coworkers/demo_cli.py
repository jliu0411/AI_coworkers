"""Dependency-light deterministic demo: python demo_cli.py"""
import json
from agents.daily_tech_agent import run_daily
from agents.career_coach_agent import find_jobs,start_interview,answer_question
from evaluation.metrics import evaluate_daily,evaluate_interview
from memory.store import init_db,load_profile,list_weaknesses,get_interview
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    init_db()
    print('\n== DAILY TECH UPGRADE AGENT: DEMO ==')
    brief=run_daily(mode='demo')
    for idx,a in enumerate(brief['articles'],1):
        print(f"{idx}. {a['title']} ({a['source']}, {a['published']})\n   {a['url']}\n   {a['summary'][:170]}")
    print('Daily eval:',json.dumps(evaluate_daily(brief),indent=2))

    print('\n== CAREER COACH AGENT: DEMO ==')
    found=find_jobs('demo')
    for j in found['jobs']:
        print(j['title'],'match heuristic:',j['match']['score'])
    job=next((j for j in found['jobs'] if 'AI Engineer' in j['title']),found['jobs'][0])
    session=start_interview(job)
    report=None
    for i in range(len(session['questions'])):
        q=get_interview(session['id'])['questions'][i]
        print(f'Question {i+1}: {q["question"]}')
        # Answer according to each question's rubric to demonstrate evaluation end-to-end.
        if i==0:
            answer='I am not sure how this works yet.'
        elif q['topic']=='RAG':
            answer=('First, create embeddings for document chunks and store the vectors. '
                    'For each user request, retrieve the most relevant chunks, then provide '
                    'them to the generator. Evaluate retrieval with precision@k and recall@k.')
        elif q.get('type')=='coding':
            answer=("import re\ndef count_words(text):\n"
                    "    words = re.findall(r'[a-z0-9]+', text.lower())\n"
                    "    counts = {}\n"
                    "    for word in words:\n"
                    "        counts[word] = counts.get(word, 0) + 1\n"
                    "    return counts")
        else:
            answer='I would address '+', '.join(q['keywords'])+' and validate it with tests and measurements.' 
        report=answer_question(session['id'],answer)
        print('Score:',report['answers'][-1]['result']['score'])
    print('Career eval:',json.dumps(evaluate_interview(report),indent=2))
    print('Learning gaps:',json.dumps(list_weaknesses()))
    # Demonstrate how the career assessment changes the next article-ranking context.
    personalized=run_daily(mode='demo')
    output=ROOT/'outputs'
    output.mkdir(exist_ok=True)
    (output/'sample_daily_brief.json').write_text(json.dumps(personalized,indent=2,ensure_ascii=False))
    (output/'sample_career_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    (output/'sample_evaluation.json').write_text(json.dumps({'daily':evaluate_daily(personalized),'career':evaluate_interview(report)},indent=2))
    print('Next brief first article:',personalized['articles'][0]['title'])
    print('DONE (SQLite progress and sample JSON reports saved in outputs/)')

if __name__=='__main__':main()
