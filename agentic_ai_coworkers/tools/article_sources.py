"""Trusted technical RSS/Atom sources. Never manufacture titles, URLs or dates in live mode."""
import calendar
import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import requests

SOURCES = {
    'AWS Machine Learning': 'https://aws.amazon.com/blogs/machine-learning/feed/',
    'Microsoft Developer Blogs': 'https://devblogs.microsoft.com/python/feed/',
    'Google Developers': 'https://developers.googleblog.com/feeds/posts/default?alt=rss',
    'LangChain': 'https://blog.langchain.com/rss/',
    'IEEE Spectrum': 'https://spectrum.ieee.org/feeds/feed.rss',
    'ACM Communications': 'https://cacm.acm.org/feed/',
}
USER_AGENT = 'SJSU-DailyTechUpgradeAgent/1.0 (educational RSS reader)'

def clean_text(s):
    s = re.sub(r'<[^>]*>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def _childtext(e, name):
    for x in e.iter():
        if x.tag.split('}')[-1] == name:
            return (x.text or '').strip()
    return ''

def _date(raw):
    if not raw: return ''
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(raw)
        return dt.date().isoformat()
    except (TypeError, ValueError, IndexError): pass
    try: return datetime.fromisoformat(raw.replace('Z','+00:00')).date().isoformat()
    except ValueError: return raw[:10] if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw[:10]) else ''

def parse_feed(xml_bytes, source):
    """Standard-library RSS/Atom parser; returns only entries with real dates and URLs."""
    root = ET.fromstring(xml_bytes)
    entries = [n for n in root.iter() if n.tag.split('}')[-1] in ('item','entry')]
    items = []
    for e in entries:
        title = clean_text(_childtext(e,'title'))
        url = _childtext(e,'link')
        if not url:
            for x in e.iter():
                if x.tag.split('}')[-1]=='link' and x.attrib.get('href'):
                    url=x.attrib['href'];break
        published = _date(_childtext(e,'pubDate') or _childtext(e,'published') or _childtext(e,'updated') or _childtext(e,'date'))
        raw_summary = _childtext(e,'description') or _childtext(e,'summary') or _childtext(e,'encoded')
        if title and url.startswith(('https://','http://')) and published:
            items.append({'title':title,'source':source,'url':url,'published':published,
                          'excerpt':clean_text(raw_summary)[:1200]})
    return items

def fetch_articles(timeout=8):
    result, errors = [], []
    for source, url in SOURCES.items():
        try:
            r = requests.get(url, headers={'User-Agent':USER_AGENT}, timeout=timeout)
            r.raise_for_status()
            result.extend(parse_feed(r.content,source)[:30])
        except (requests.RequestException,ET.ParseError,ValueError) as exc:
            errors.append(f'{source}: {type(exc).__name__}')
    seen, unique = set(), []
    for article in result:
        key=article['url'].split('?')[0].rstrip('/')
        if key not in seen:
            unique.append(article);seen.add(key)
    return unique,errors

def article_score(article, profile, weaknesses, read_urls, now=None):
    now = now or datetime.now(timezone.utc).date()
    text = (article['title']+' '+article.get('excerpt','')).lower()
    topics = profile.get('interests',[])
    score = 0
    for t in topics:
        tokens = [w for w in re.findall(r'\w+', t.lower()) if len(w)>2]
        if any(w in text for w in tokens): score += 3
    for gap in weaknesses:
        tokens=[w for w in re.findall(r'\w+',gap['topic']) if len(w)>2]
        if any(w in text for w in tokens): score += 4 * gap.get('weight',1)
    try:
        days = (now - datetime.strptime(article['published'],'%Y-%m-%d').date()).days
        if days < 0: return -999
        score += max(0, 15-min(days,90)/6)
    except ValueError: pass
    if article['url'] in read_urls: score -= 35
    if len(article.get('excerpt','')) > 80: score += 2
    return round(score,2)

def best_articles(articles, profile, weaknesses, read_urls, count=3):
    ranked = sorted(articles,key=lambda a:article_score(a,profile,weaknesses,read_urls),reverse=True)
    return ranked[:count]
