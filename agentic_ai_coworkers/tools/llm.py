"""Optional OpenAI analysis. Strict JSON decoding with an explicit extractive fallback."""
import json
import os
import re

def is_enabled():
    return bool(os.getenv('OPENAI_API_KEY','').strip())

def get_model():
    return os.getenv('OPENAI_MODEL','gpt-5-mini')

def response_json(instructions, user_text):
    if not is_enabled(): raise RuntimeError('OPENAI_API_KEY is not set')
    from openai import OpenAI
    client=OpenAI(timeout=45, max_retries=1)
    response=client.responses.create(model=get_model(), instructions=instructions,
            input=user_text, text={'format':{'type':'json_object'}}, max_output_tokens=1100)
    text=response.output_text.strip()
    # Some model configurations may surround the response with markdown fences.
    text=re.sub(r'^```(?:json)?\s*|\s*```$', '', text).strip()
    return json.loads(text)

def extractive_summary(article,profile):
    excerpt=article.get('excerpt','').strip()
    if not excerpt:
        summary='The feed provides a title and link but no extract. Open the source for technical details.'
        takeaways=['Review the original article before drawing technical conclusions.']
    else:
        sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',excerpt) if x.strip()]
        summary=(sentences[0] if sentences else excerpt)[:430]
        # Use other source sentences for non-redundant takeaways when available.
        takeaways=[x[:230] for x in sentences[1:3]] or [summary]
    goals=', '.join(profile.get('target_roles',[])[:2]) or 'technical development'
    return {'summary':summary,'takeaways':takeaways,
            'why_it_matters':f'This article matches your technical interests and can support preparation for {goals}.',
            'method':'extractive (not model-generated)'}

def summarize_article(article, profile, use_ai):
    if not use_ai:
        return extractive_summary(article,profile)
    instructions=('You are a precise technical learning assistant. Use ONLY the supplied article excerpt; '
                  'do not infer unmentioned experiments, metrics, or results. Return valid JSON with keys '
                  'summary (1-3 sentences), takeaways (array of 2 short strings), why_it_matters (1 sentence). '
                  'If the excerpt is insufficient, explicitly acknowledge that.')
    payload={'article': article, 'user_interests':profile.get('interests',[]),
             'career_goals':profile.get('target_roles',[])}
    try:
        data=response_json(instructions,json.dumps(payload))
        if not isinstance(data.get('takeaways'),list) or not data.get('summary'):raise ValueError('Malformed model response')
        return {'summary':str(data['summary'])[:650],
                'takeaways':[str(s)[:250] for s in data['takeaways'][:3]],
                'why_it_matters':str(data.get('why_it_matters',''))[:350],
                'method':'AI summary grounded in feed excerpt'}
    except Exception as exc:
        result=extractive_summary(article,profile)
        result['warning']=f'AI unavailable ({type(exc).__name__}); used extractive summary.'
        return result
