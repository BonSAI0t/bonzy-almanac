#!/usr/bin/env python3
"""Parse Project Zomboid B42 script dump + EN translations into almanac.json.
usage: almanac_parse.py <generated_dir> <translate_EN_dir> <out.json>"""
import os,re,json,sys,collections
GEN,TR,OUT=sys.argv[1:4]
def tj(n):
    try: return json.load(open(os.path.join(TR,n),encoding='utf-8'))
    except Exception: return {}
T_REC=tj('Recipes.json'); T_ITEM=tj('ItemName.json'); T_UI=tj('UI.json'); T_IG=tj('IG_UI.json'); T_ENT=tj('Entity.json')
kv=re.compile(r'^\s*([A-Za-z_][\w]*)\s*=\s*(.*?),?\s*$')
recipes={}; items={}; profs={}; traits={}
def parse_input(s):
    s=s.rstrip(',')
    m=re.match(r'item\s+(\d+(?:\.\d+)?)\s+(tags\[[^\]]*\]|\[[^\]]*\])(.*)$',s)
    if m:
        cnt,what,rest=m.groups()
        mode=(re.search(r'mode:(\w+)',rest) or [None,''])[1]
        flags=(re.search(r'flags\[([^\]]*)\]',rest) or [None,''])[1]
        if what.startswith('tags'):
            ids=[x for x in what[5:-1].split(';') if x]; kind='tag'
        else:
            ids=[x for x in what[1:-1].split(';') if x]; kind='item'
        return {'t':kind,'n':cnt,'ids':ids,'mode':mode,'flags':[f for f in flags.split(';') if f]}
    m=re.match(r'-fluid\s+([\d\.]+)\s+\[([^\]]*)\](.*)$',s)
    if m: return {'t':'fluid','n':m.group(1),'ids':[x for x in m.group(2).split(';') if x],'mode':'','flags':[]}
    return None
def parse(path):
    rel=os.path.relpath(path,GEN).replace('\\','/')
    stack=[];pending=None
    for ln in open(path,encoding='utf-8',errors='replace'):
        s=re.sub(r'//.*','',ln).strip()
        if not s: continue
        if s=='{': stack.append({'h':pending or '','kv':{},'in':[],'out':[]}); pending=None; continue
        if s.startswith('}'):
            if stack: finish(stack.pop(),stack,rel)
            continue
        top=stack[-1] if stack else None
        if top and top['h']=='inputs' and len(stack)>=2:
            p=parse_input(s)
            if p: stack[-2]['in'].append(p)
            continue
        if top and top['h']=='outputs' and len(stack)>=2:
            m=re.search(r'item\s+([\d\.]+)\s+([\w\.]+)',s)
            if m: stack[-2]['out'].append([m.group(1),m.group(2)])
            continue
        m=kv.match(s)
        if m and top is not None: top['kv'][m.group(1)]=m.group(2).rstrip(',').strip(); continue
        pending=s
def finish(b,stack,rel):
    h=b['h'].split(); k=b['kv']
    if not h: return
    if h[0]=='craftRecipe' or h[:2]==['component','CraftRecipe']:
        if h[0]=='craftRecipe': name=h[1]; kind='Craft'
        else: name=stack[-1]['h'].split()[-1] if stack else '?'; kind='Build'
        r=recipes.setdefault(name,{'id':name,'kind':kind,'file':rel})
        r.update(k); r['in']=b['in']; r['out']=b['out']
    elif h[0]=='item' and len(h)==2: items[h[1]]=k
    elif h[0]=='character_profession_definition': profs[h[1]]=k
    elif h[0]=='character_trait_definition': traits[h[1]]=k
for dp,_,fs in os.walk(GEN):
    for f in fs:
        if f.endswith('.txt'): parse(os.path.join(dp,f))
SK_ALIAS={'Sneak':'Sneaking','Lightfoot':'Lightfooted','PlantScavenging':'Foraging','Sprinting':'Sprinting'}
def skname(s): return T_IG.get('IGUI_perks_'+SK_ALIAS.get(s,s)) or T_IG.get('IGUI_perks_'+s) or s
def sklist(v,sep=':'):
    out=[]
    for x in (v or '').split(';'):
        if sep in x: a,b=x.split(sep,1); out.append([a.strip(),int(float(b))])
    return out
def human(x): return re.sub(r'(?<=[a-z])(?=[A-Z0-9])',' ',x).replace('_',' ').strip()
def iname(i):
    i=re.sub(r'^\d+:','',i)
    full=i if '.' in i else 'Base.'+i
    short=full.split('.')[-1]
    return T_ITEM.get(full) or T_ITEM.get(i) or (items.get(short) or {}).get('DisplayName') or human(short)
def lst(v): return [x.strip() for x in (v or '').split(';') if x.strip()]
# research / literature indexes
research=collections.defaultdict(set); learned=collections.defaultdict(set)
for iid,k in items.items():
    for r in lst(k.get('Researchablerecipes')): research[r].add(iid)
    for r in lst(k.get('LearnedRecipes')): learned[r].add(iid)
meta=collections.defaultdict(list)
for n,r in recipes.items():
    if r.get('MetaRecipe'): meta[r['MetaRecipe']].append(n)
names={}
out_rec=[]
for n,r in sorted(recipes.items(),key=lambda x:x[0].lower()):
    if r.get('OnAddToMenu')=='debugTest' or r.get('category')=='Debug': continue
    tags=r.get('Tags') or ''
    books=set(learned.get(n,()))
    if r.get('MetaRecipe'): books|=set(learned.get(r['MetaRecipe'],()))
    outs=[o for o in r['out'] if o[1]!='mapper']
    rec={'id':n,'name':T_REC.get(n) or T_ENT.get(n) or re.sub(r'(?<=[a-z])(?=[A-Z])',' ',n).replace('_',' '),
         'kind':r['kind'],'cat':r.get('category',''),'learn':(r.get('NeedToBeLearn','').lower()=='true'),
         'skill':sklist(r.get('SkillRequired')),'any':sklist(r.get('AutoLearnAny')),'all':sklist(r.get('AutoLearnAll')),
         'rlvl':r.get('ResearchSkillLevel',''),'rtag':'Cannot' if 'CannotBeResearched' in tags else ('Always' if 'CanAlwaysBeResearched' in tags else ''),
         'rItems':sorted(research.get(n,())),'rOut':[] if 'CannotBeResearched' in tags else sorted({o[1].replace('Base.','') for o in outs}),
         'books':sorted(books),'meta':r.get('MetaRecipe','').replace('base:',''),
         'in':r['in'],'out':outs,'file':r['file']}
    out_rec.append(rec)
def tid(x): return x.replace('base:','')
P=[]
for pid,k in profs.items():
    i=tid(pid); P.append({'id':i,'name':T_UI.get(k.get('UIName',''),i),'cost':int(k.get('Cost',0) or 0),
      'xp':sklist(k.get('XPBoosts'),'='),'traits':[tid(x) for x in lst(k.get('GrantedTraits'))],'recipes':lst(k.get('GrantedRecipes'))})
TR_=[]
for t,k in traits.items():
    i=tid(t); TR_.append({'id':i,'name':T_UI.get(k.get('UIName',''),i),'desc':T_UI.get(k.get('UIDescription',''),''),
      'cost':int(k.get('Cost',0) or 0),'prof':k.get('IsProfessionTrait','false').lower()=='true',
      'mp_off':k.get('DisabledInMultiplayer','false').lower()=='true',
      'xp':sklist(k.get('XPBoosts'),'='),'recipes':lst(k.get('GrantedRecipes')),
      'excl':[tid(x) for x in lst(k.get('MutuallyExclusiveTraits'))]})
# names for every id referenced
ids=set()
for r in out_rec:
    for c in r['in']:
        if c['t']=='item': ids.update(c['ids'])
    for o in r['out']: ids.add(o[1])
    ids.update(r['rItems']); ids.update(r['books']); ids.update(r['rOut'])
INAMES={i:iname(i) for i in ids}
tagitems=collections.defaultdict(list)
for iid,k in items.items():
    for t in lst(k.get('Tags')): tagitems[t.lower()].append(iid)
used_tags={t for r in out_rec for c in r['in'] if c['t']=='tag' for t in c['ids']}
lower_items={k.lower():k for k in items}
VOC=set()
for v in list(T_ITEM.values())+list(T_REC.values()):
    for w in re.findall(r"[A-Za-z]+",str(v)): 
        if len(w)>1: VOC.add(w.lower())
VOC|={'smeltable','sealed','refillable','dyed','divided','dig','grave','peg','misc','start','tiny','masons','into','sharpen','sharp','crude','sinew','be','can','uses','fat','fiber','binding','gives','normal','hold','sharpenable','repairable','uncut','mixing','utensil','break','pick'}
def seg(w):
    w=w.lower(); n=len(w); best=[None]*(n+1); cost=[1e9]*(n+1); best[0]=[]; cost[0]=0
    for i in range(n):
        if best[i] is None: continue
        for j in range(i+1,n+1):
            p=w[i:j]
            c=1 if p in VOC else (10*len(p))
            if cost[i]+c<cost[j]: cost[j]=cost[i]+c; best[j]=best[i]+[p]
    return ' '.join(x.capitalize() for x in best[n]).replace('Misc','Misc.')
TAGS={}
for t in used_tags:
    short=t.split(':')[-1]; mem=sorted(tagitems.get(t.lower(),[]))
    lab=seg(short)
    TAGS[t]={'name':lab,'items':[iname(x) for x in mem][:40],'more':max(0,len(mem)-40)}
SK=sorted({s for r in out_rec for s,_ in r['skill']+r['any']+r['all']}|{s for p in P+TR_ for s,_ in p['xp']})
json.dump({'recipes':out_rec,'profs':sorted(P,key=lambda x:x['name']),'traits':sorted(TR_,key=lambda x:x['name']),
  'items':INAMES,'tags':TAGS,'skills':{s:skname(s) for s in SK}},open(OUT,'w',encoding='utf-8'),separators=(',',':'),ensure_ascii=False)
print('recipes',len(out_rec),'learnable',sum(r['learn'] for r in out_rec),'profs',len(P),'traits',len(TR_),'items',len(INAMES),'bytes',os.path.getsize(OUT))
