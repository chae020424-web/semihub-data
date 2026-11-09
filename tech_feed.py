"""Public newsroom RSS crawler. Keep headline/date/link only; no article copying."""
import re,html,email.utils,datetime,urllib.parse,urllib.request
from xml.etree import ElementTree as ET

COMPANIES=[
 ('SK하이닉스','https://news.skhynix.com/en/feed/','news.skhynix.com'),
 ('삼성전자','https://news.samsungsemiconductor.com/kr/feed/','news.samsungsemiconductor.com'),
 ('삼성전자','https://news.samsung.com/global/feed','news.samsung.com'),
]
SEARCH=[('SK하이닉스','site:news.skhynix.com/en/ HBM OR semiconductor OR chip OR packaging'),('삼성전자','site:news.samsungsemiconductor.com/kr/ 반도체 OR 패키징 OR HBM'),('ASML','site:investor.asml.com/news-releases EUV OR lithography'),('TSMC','site:pr.tsmc.com/english/news semiconductor'),('Micron','site:micron.com/about/press/news memory OR HBM')]
TECH_TERMS=['hbm','dram','nand','tsv','bond','패키징','euv','포토','2nm','chiplet','패키지','공정','메모리','gddr','ssd','cxl','cpo','photonics','반도체','silicon','semiconductor','metrology','packaging','fab','foundry','technology','technologies','cooling','광통신','실리콘','3d','ai','equipment','포토닉스']
KEYS={
 '패키징':['패키징','package','packaging','bond','tsv','chiplet','interposer','cowos','냉각'],
 '노광·장비':['euv','asml','lithography','photomask','노광','포토마스크'],
 '메모리':['hbm','dram','nand','memory','ssd','메모리','낸드','d램','hbf'],
 '광통신':['photonics','cpo','광통신','포토닉스'],
 'AI·시스템':['cxl','gpu','ai infra','pim'],
}
RELATED={'hbm4':['hbm','dram','hbm4','zhbm'],'hybrid':['bonding','본딩'], 'tsv':['tsv'], 'cowos':['packaging','패키징','chiplet','cowos','interposer'], 'si':['si/pi','signal integrity'], 'highna':['high-na','high na','euv','lithography','photomask','노광'], 'gaa':['gaa','2nm','nanosheet'],'cpo':['cpo','photonics','포토닉스'], 'cxl':['cxl'], 'hbf':['hbf'], 'nand':['nand','낸드'],'pim':['pim'], 'thermal':['냉각','cooling','thermal']}

def clean(s):
    s=re.sub('<[^>]*>',' ',str(s or ''))
    return re.sub(r'\s+',' ',html.unescape(s)).strip()

def request(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (SEMI-HUB educational RSS reader)','Accept':'application/rss+xml,application/xml,application/atom+xml,*/*'})
    with urllib.request.urlopen(req,timeout=12) as resp:return resp.read(1500000)

def date_of(s):
    if not s:return ''
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d')
    except Exception:
        m=re.search(r'20\d\d-\d\d-\d\d',s)
        return m.group(0) if m else ''

def classify(title):
    lo=title.lower()
    cat=next((c for c,ls in KEYS.items() if any(t in lo for t in ls)),'기타')
    rel=[t for t,ls in RELATED.items() if any(x in lo for x in ls)][:5]
    return cat,rel

def parse(xml,company):
    root=ET.fromstring(xml)
    rows=[]
    for item in root.findall('.//item'):
        def val(t):return item.findtext(t) or ''
        title=clean(val('title'))[:240]
        link=clean(val('link'))
        desc=clean(val('description'))[:125]
        published=date_of(val('pubDate') or val('date'))
        if not (title and link.startswith('https://') and published):continue
        if not any(x in (title+' '+desc).lower() for x in TECH_TERMS):continue
        cat,rel=classify(title+' '+desc[:80])
        rows.append(dict(title=title,url=link,date=published,company=company,category=cat,topics=rel,summary=desc,source=company))
    return rows

def gather():
    rows=[];errors=[]
    for company,url,_ in COMPANIES:
        try:rows.extend(parse(request(url),company))
        except Exception as ex:errors.append(company+' RSS: '+type(ex).__name__)
    # Fallback for sources with no known public RSS.
    for company,query in SEARCH:
        try:
            url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query+' when:14d','hl':'ko','gl':'KR','ceid':'KR:ko'})
            n=parse(request(url),company)
            rows.extend(n)
        except Exception as ex:errors.append(company+' 뉴스 검색: '+type(ex).__name__)
    today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    unique=set();out=[]
    for n in sorted(rows,key=lambda x:x['date'],reverse=True):
        try:d=datetime.date.fromisoformat(n['date'])
        except ValueError:continue
        if d>today or d.year<2025:continue
        k=(n['title'].lower(),n['date'])
        if k in unique:continue
        unique.add(k);out.append(n)
    return out[:150],errors
