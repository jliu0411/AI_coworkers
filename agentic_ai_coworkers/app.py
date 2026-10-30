"""Streamlit front end for two SJSU Agentic AI Coworkers."""
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import streamlit as st

from agents.daily_tech_agent import run_daily
from agents.career_coach_agent import find_jobs,start_interview,answer_question,manual_job
from tools.job_sources import DEFAULT_BOARDS,rank_jobs
from tools.venture_ideas import propose_ideas,venture_coaching_case
from tools.graph_runtime import LANGGRAPH_AVAILABLE
from tools.llm import is_enabled
from evaluation.metrics import evaluate_daily,evaluate_interview
from memory.store import (init_db,load_profile,save_profile,mark_read,
                          list_briefs,dashboard_stats,assessment_history,
                          list_weaknesses,get_interview)

st.set_page_config(page_title='AI Coworkers | SJSU',page_icon='🎓',layout='wide')
st.markdown('''<style>
.block-container{max-width:1180px;padding-top:2rem}
h1,h2,h3{letter-spacing:-.025em}
div[data-testid="stMetric"]{background:rgba(110,115,130,.06);border:1px solid rgba(115,115,120,.2);border-radius:12px;padding:14px}
</style>''',unsafe_allow_html=True)
init_db()

st.title('🎓 My Agentic AI Coworkers')
st.caption('Two personalized agents • Daily learning and career preparation • Persistent SQLite memory')

with st.sidebar:
    st.header('⚙️ Settings')
    mode=st.radio('Data mode',['Demo','Live'],help='Demo uses labeled historical article fixtures and fictional jobs. Live attempts real RSS / Greenhouse fetches.')
    use_ai=st.checkbox('Use OpenAI for analysis',disabled=(mode=='Demo' or not is_enabled()),
                        help='Requires OPENAI_API_KEY in .env; otherwise shows grounded extractive summaries and demo interview scoring.')
    st.caption(f'OpenAI API key: {"configured" if is_enabled() else "not configured"}')
    st.caption(f'Agent framework: {"LangGraph" if LANGGRAPH_AVAILABLE else "test-only sequential fallback (install requirements)"}')
    st.divider()
    st.subheader('Personal profile')
    profile=load_profile()
    with st.form('profile_form'):
        name=st.text_input('Name / alias',profile.get('name','Student'))
        interests=st.text_area('Technical interests (comma-separated)',', '.join(profile.get('interests',[])),height=74)
        skills=st.text_area('Current skills (comma-separated)',', '.join(profile.get('skills',[])),height=74)
        roles=st.text_area('Target roles (comma-separated)',', '.join(profile.get('target_roles',[])),height=74)
        location=st.text_input('Preferred location',profile.get('preferred_location','California or Remote'))
        save=st.form_submit_button('Save profile',use_container_width=True)
    if save:
        updated={'name':name.strip() or 'Student','interests':[x.strip() for x in interests.split(',') if x.strip()],
                 'skills':[x.strip() for x in skills.split(',') if x.strip()],
                 'target_roles':[x.strip() for x in roles.split(',') if x.strip()],
                 'preferred_location':location.strip()}
        save_profile(updated)
        st.success('Saved. Both agents now use this profile.')
    st.caption('Your profile and answers are stored locally. OpenAI is contacted only if AI analysis is enabled.')

tech_tab,career_tab,progress_tab,eval_tab=st.tabs(['📚 Daily Tech Brief','💼 Career Coach','📈 Progress','🧪 Evaluation'])

with tech_tab:
    st.subheader('DailyTechUpgradeAgent')
    st.write('Find three high-quality technical articles, explain the key takeaways, and connect them to your goals.')
    left,right=st.columns([1,3])
    with left:
        generate=st.button('Discover top 3',type='primary',use_container_width=True)
    if generate:
        with st.spinner('Searching, ranking, and summarizing technical sources...'):
            try:st.session_state['brief']=run_daily(mode.lower(),use_ai)
            except Exception as e:st.error(f'Article workflow failed: {e}')
    brief=st.session_state.get('brief')
    if brief:
        if brief['mode']=='demo':st.info(brief['note'])
        else:st.caption(brief['note'])
        c1,c2,c3=st.columns(3)
        c1.metric('Articles',len(brief['articles']))
        c2.metric('Planned reading',f"{brief['planned_reading_minutes']} min")
        c3.metric('Result','3 of 3' if brief['status']=='complete' else 'Partial')
        if brief['status']!='complete':
            st.warning('The live sources returned fewer than 3 valid dated articles. No additional stories were invented.')
        if brief['warnings']:
            with st.expander('Unreachable sources / warnings'):
                for err in brief['warnings']:st.write('•',err)
        for i,a in enumerate(brief['articles'],1):
            with st.container(border=True):
                st.markdown(f"#### {i}. {a['title']}")
                st.caption(f"{a['source']} • {a['published']} • {a['reading_minutes']} min • {a['method']}")
                st.markdown(f"**Original article:** {a['url']}")
                st.write(a['summary'])
                st.markdown('**Technical takeaways**')
                for t in a.get('takeaways',[]):st.write('•',t)
                st.markdown('**Career value**')
                st.write(a.get('why_it_matters',''))
                if a.get('warning'):st.warning(a['warning'])
                if st.button('Mark as read',key=f"read_{i}_{a['url']}"):
                    mark_read(a['url']);st.success('Saved to learning history.')
        st.download_button('Download daily brief (JSON)',data=json.dumps(brief,indent=2),
                           file_name='daily_tech_brief.json',mime='application/json')
    else:
        st.info('Choose **Discover top 3** to generate the first brief. Demo mode works offline.')

with career_tab:
    st.subheader('nextLevelPersonalCoachForCareerLevel')
    st.write('Discover opportunities, compare the required skills, then complete a three-question technical interview.')
    if mode=='Demo':st.info('Demo openings are fictional examples, not currently open positions.')
    search_tab,paste_tab,venture_tab=st.tabs(['Find opportunities','Paste a job description','Startup idea lab'])
    with search_tab:
        boards=st.text_input('Greenhouse board tokens (comma-separated)',', '.join(DEFAULT_BOARDS),
                             help='Only used for Live mode. These are company board slugs, not company names or job-search terms.')
        if st.button('Find job matches',type='primary'):
            with st.spinner('Searching job boards and matching skills...'):
                try:
                    st.session_state['jobs_result']=find_jobs(mode.lower(),[x.strip() for x in boards.split(',') if x.strip()])
                except Exception as e:st.error(f'Job search failed: {e}')
        category_filter=st.selectbox('Opportunity type',['All','Job','Internship','Research'],index=0)
        res=st.session_state.get('jobs_result')
        if res:
            st.caption(f"{res['mode'].title()} data • {res['fetched']} total postings found • top {len(res['jobs'])} displayed")
            if res['errors']:
                with st.expander('Source errors'):
                    for err in res['errors']:st.write('•',err)
            if not res['jobs']:st.warning('No jobs found from the specified boards. Try a different board token or paste a description.')
            filtered_jobs=[j for j in res['jobs'] if category_filter=='All' or j.get('category')==category_filter]
            for i,j in enumerate(filtered_jobs):
                with st.container(border=True):
                    c1,c2=st.columns([5,1])
                    with c1:
                        st.markdown(f"**{j['title']}** — {j['company']}")
                        st.caption(f"{j['location']} • {j['source']} • {j.get('category','Job')}")
                    with c2:st.metric('Match*',f"{j['match']['score']}/100")
                    if j.get('url'):st.markdown(f"[Original job posting]({j['url']})")
                    st.write('**Skills matched:**',', '.join(j['match']['matched_skills']) or 'None detected')
                    st.write('**Possible skill gaps:**',', '.join(j['match']['missing_skills']) or 'None detected')
                    if st.button('Practice interview for this role',key=f'interview_job_{i}'):
                        iv=start_interview(j)
                        st.session_state['interview_id']=iv['id']
                        st.session_state.pop('last_report',None)
                        st.rerun()
            st.caption('*Transparent matching heuristic, not hiring likelihood or proof of qualification.')
    with paste_tab:
        with st.form('paste_job'):
            title=st.text_input('Job title','AI Engineer')
            description=st.text_area('Job description',height=180,placeholder='Paste a real job description or a study scenario here...')
            submitted=st.form_submit_button('Analyze and start interview')
        if submitted:
            if len(description.strip())<30:st.error('Paste at least 30 characters of job requirements.')
            else:
                j=manual_job(title,description)
                j['match']=rank_jobs([j],load_profile())[0]['match']
                st.session_state['manual_job']=j
                iv=start_interview(j)
                st.session_state['interview_id']=iv['id']
                st.session_state.pop('last_report',None)
                st.success('Job analyzed. Interview started below.')
                st.write('Detected gaps:',', '.join(j['match']['missing_skills']) or 'None')
    with venture_tab:
        st.caption('These are potential venture ideas based on your interests, NOT verified market demand, grants, or funded openings.')
        venture_list=propose_ideas(load_profile())
        for idx,idea in enumerate(venture_list):
            with st.container(border=True):
                st.markdown(f"**{idea['title']}**")
                st.write('**Potential customer:**',idea['customer'])
                st.write('**Problem to investigate:**',idea['problem'])
                st.write('**Minimal prototype:**',idea['mvp'])
                st.write('**Validation experiment:**',idea['validate'])
                st.write('**Biggest risk:**',idea['risk'])
                if st.button('Practice founder interview',key=f'venture_{idx}'):
                    iv=start_interview(venture_coaching_case(idea))
                    st.session_state['interview_id']=iv['id']
                    st.session_state.pop('last_report',None)
                    st.rerun()
    st.divider()
    st.markdown('### Interactive technical / founder assessment')
    interview_id=st.session_state.get('interview_id')
    iv=get_interview(interview_id) if interview_id else None
    if iv:
        st.caption(f"Role: {iv['job']['title']} • Completed {iv['current_index']}/{len(iv['questions'])} questions")
        for r in iv['responses']:
            with st.expander(f"Previous: {r['topic']} — {r['result']['score']}/100"):
                st.write('**Your answer:**',r['answer'])
                st.write('**Feedback:**',r['result']['feedback'])
                if r['result'].get('warning'):st.warning(r['result']['warning'])
        if iv['finished']:
            st.success('Interview complete! Your report is saved in SQLite.')
            report=st.session_state.get('last_report')
            if not report:
                responses=iv['responses'];avg=round(sum(r['result']['score'] for r in responses)/len(responses),1)
                report={'interview_id':iv['id'],'job_title':iv['job']['title'],'questions_completed':len(responses),
                        'total_questions':len(iv['questions']),'average_score':avg,'complete':True,
                        'answers':responses,'improvement_topics':list(dict.fromkeys(r['topic'] for r in responses if r['result']['score']<70)),
                        'next_steps':['Study the weakest topic using the Daily Tech agent','Practice missing concepts','Repeat a similar technical assessment']}
            st.metric('Interview average',f"{report['average_score']}/100")
            st.write('**Study next:**',', '.join(report.get('improvement_topics',[])) or 'Review all feedback and practice again')
            st.download_button('Download career readiness report (JSON)',json.dumps(report,indent=2),
                               file_name='career_readiness_report.json',mime='application/json')
        else:
            q=iv['questions'][iv['current_index']]
            st.markdown(f"**Question {iv['current_index']+1}: {q['question']}**")
            with st.form(f"answer_{iv['id']}_{iv['current_index']}"):
                answer=st.text_area('Your answer',height=140,placeholder='Explain your reasoning, relevant tools, and tradeoffs.')
                send=st.form_submit_button('Submit answer and get feedback',type='primary')
            if send:
                if not answer.strip():st.error('Enter an answer first.')
                else:
                    with st.spinner('Evaluating answer and updating skill memory...'):
                        try:
                            report=answer_question(iv['id'],answer,use_ai)
                            st.session_state['last_report']=report
                            grade=report['answers'][-1]['result']
                            st.success(f"Score: {grade['score']}/100 ({grade['method']})")
                            st.write(grade['feedback'])
                            if grade.get('missing'):st.write('Review:',', '.join(grade['missing']))
                            if grade.get('warning'):st.warning(grade['warning'])
                            st.caption('Your response, score, and any learning gap have been saved.')
                            st.button('Load next question')
                        except Exception as e:st.error(f'Could not evaluate: {e}')
    else:
        st.info('Select a job from the discovery results or paste a job description to begin.')

with progress_tab:
    st.subheader('Your learning and career history')
    stats=dashboard_stats()
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Saved briefs',stats['briefs'])
    c2.metric('Articles read',stats['articles_read'])
    c3.metric('Questions evaluated',stats['questions_answered'])
    c4.metric('Completed interviews',stats['interviews_completed'])
    gaps=list_weaknesses()
    st.markdown('**Detected topics to revisit**')
    if gaps:
        for g in gaps:st.write(f"• {g['topic'].title()} (priority {g['weight']})")
        st.caption('These priorities directly influence ranking in your next Daily Tech Brief.')
    else:st.info('No weak topics recorded yet. Complete an interview assessment to build your learning plan.')
    history=assessment_history()
    if history:
        st.markdown('**Assessment history**')
        st.dataframe(history,use_container_width=True,hide_index=True)
    briefs=list_briefs(limit=5)
    if briefs:
        st.markdown('**Most recent briefs**')
        for b in briefs:
            st.write(f"• {b['created_at'][:10]} | {len(b['articles'])} articles | {b['mode']} mode")

with eval_tab:
    st.subheader('Evaluation methods and current measurements')
    st.write('The prototype separates automatically measured checks from subjective assessment quality that requires human evaluation.')
    brief=st.session_state.get('brief')
    if brief:
        st.markdown('**Article quality checks**')
        st.json(evaluate_daily(brief))
    else:st.info('Generate a daily brief to display measured article metadata metrics.')
    report=st.session_state.get('last_report')
    if report:
        st.markdown('**Interview checks**')
        st.json(evaluate_interview(report))
    else:st.info('Answer interview questions to display the available scoring metrics.')
    st.markdown('**How to evaluate beyond the demo**')
    st.markdown('''- **Article relevance / Precision@3:** Have a person label recommended articles relevant (1) or not (0); count relevant articles divided by 3.
- **Summary faithfulness:** Manually compare each claim with the linked original article; measure supported claims / total factual claims.
- **Job relevance:** Label whether each opportunity meets target role, location, and experience constraints.
- **Interview grading agreement:** Compare AI/keyword scores to a human-graded answer set and compute mean absolute error.
- **Student progress:** Compare topic-level scores over repeated assessments; report the change, not a claim of learning causality.''')
    st.caption('No actual accuracy or learning-improvement claim is made until labeled evaluations have been run.')
