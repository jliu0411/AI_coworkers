"""Run daily on a schedule using cron or Windows Task Scheduler.

Example: python run_daily.py --mode live
Do not embed API keys or leave a perpetual scheduler running inside Streamlit.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime,timezone
from dotenv import load_dotenv
from agents.daily_tech_agent import run_daily

if __name__=='__main__':
    load_dotenv()
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['demo','live'],default='live')
    p.add_argument('--ai',action='store_true')
    args=p.parse_args()
    brief=run_daily(args.mode,args.ai)
    folder=Path(__file__).resolve().parent/'outputs'; folder.mkdir(exist_ok=True)
    path=folder/f'daily_brief_{datetime.now(timezone.utc):%Y%m%d}.json'
    path.write_text(json.dumps(brief,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Saved {len(brief["articles"])} articles to {path}')
    if brief['status']!='complete':print('Warning: fewer than 3 validated sources were available')
