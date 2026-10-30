"""Personalized business *hypotheses*, not validated market openings or funding calls."""

def propose_ideas(profile):
    interests=' '.join(profile.get('interests',[])).lower()
    skills=' '.join(profile.get('skills',[])).lower()
    ai='AI assistants' if ('ai' in interests or 'rag' in interests or 'machine learning' in interests) else 'simple automation'
    stack='Python/FastAPI' if 'python' in skills else 'a lightweight web application'
    return [
        {'title':'Technical Interview Practice Copilot',
         'customer':'University students and new graduates',
         'problem':'Students may not know which interview topics to practice next.',
         'mvp':f'A {stack} app that asks questions, grades responses, and suggests exercises using {ai}.',
         'validate':'Interview 5 students, observe practice sessions, and measure whether they return for a second session.',
         'risk':'Evaluation quality, user trust, and whether students are willing to pay.'},
        {'title':'Knowledge Search for Small Organizations',
         'customer':'Local small businesses with scattered internal documents',
         'problem':'Staff may waste time searching policies, instructions, and onboarding documents.',
         'mvp':f'A simple document search prototype using {ai}, grounded responses, and citations.',
         'validate':'Speak with 5 owners or operations staff; test retrieval with 10 real questions from a consenting pilot.',
         'risk':'Document privacy, answer accuracy, and unclear buyer demand.'},
        {'title':'Research Reading and Experiment Tracker',
         'customer':'Student research groups and independent developers',
         'problem':'Papers, notes and experimental follow-ups can become disconnected.',
         'mvp':f'A {stack} dashboard that organizes paper URLs, experiments and next actions.',
         'validate':'Have two study groups trial the workflow and track completed follow-ups versus their usual process.',
         'risk':'Competition from established note-taking and literature tools.'},
    ]

def venture_coaching_case(idea):
    return {'id':'hypothesis-'+idea['title'].lower().replace(' ','-'),
            'title':'Startup Founder: '+idea['title'],
            'company':'User venture hypothesis','location':'Anywhere',
            'url':'','source':'Generated business hypothesis (NOT market-validated)',
            'mode':'venture',
            'description':f"Customer: {idea['customer']}. Problem: {idea['problem']} "
                          f"MVP: {idea['mvp']} Validation: {idea['validate']} Risk: {idea['risk']}"}
