# Build item-source flags from PZ Lua: L=loot F=forage A=animal(butcher) S=fishing T=traps
import re,os,sys,json,glob
LUA=sys.argv[1]; OUT=sys.argv[2]
src={}
def add(t,f):
    if not t or t.startswith('--'):return
    if '.' not in t:t='Base.'+t
    s=src.setdefault(t,set());s.add(f)
def strip(s):return re.sub(r'--\[\[.*?\]\]','',re.sub(r'--[^\n]*','',s),flags=re.S)
for f in glob.glob(LUA+'/server/Items/*Distribution*.lua'):
    s=strip(open(f,encoding='utf-8',errors='ignore').read())
    for m in re.finditer(r'"([A-Za-z0-9_.]+)"\s*,\s*[\d.]+',s):add(m.group(1),'L')
    for m in re.finditer(r'\bitem\s*=\s*"([A-Za-z0-9_.]+)"',s):add(m.group(1),'L')
for f in glob.glob(LUA+'/shared/Foraging/**/*.lua',recursive=True):
    s=strip(open(f,encoding='utf-8',errors='ignore').read())
    for m in re.finditer(r'"(Base\.[A-Za-z0-9_]+)"',s):add(m.group(1),'F')
for f in glob.glob(LUA+'/shared/Definitions/animal/*.lua'):
    s=strip(open(f,encoding='utf-8',errors='ignore').read())
    for m in re.finditer(r'"(Base\.[A-Za-z0-9_]+)"',s):add(m.group(1),'A')
for f in glob.glob(LUA+'/shared/Fishing/*.lua'):
    s=strip(open(f,encoding='utf-8',errors='ignore').read())
    for m in re.finditer(r'"(Base\.[A-Za-z0-9_]+)"',s):add(m.group(1),'S')
for f in glob.glob(LUA+'/shared/Traps/**/*.lua',recursive=True):
    s=strip(open(f,encoding='utf-8',errors='ignore').read())
    for m in re.finditer(r'"(Base\.[A-Za-z0-9_]+)"',s):add(m.group(1),'T')
out={k:''.join(sorted(v)) for k,v in sorted(src.items())}
json.dump(out,open(OUT,'w'),separators=(',',':'))
from collections import Counter
print(len(out),Counter(c for v in out.values() for c in v))
for k in ['Base.Nails','Base.IronScrap','Base.Stone','Base.SharpedStone','Base.Clay','Base.IronOre','Base.Twine','Base.Wire','Base.Leather_Crude_Medium_Tan','Base.Plank','Base.Log','Base.Charcoal','Base.TreeBranch2','Base.Sack']:print(k,out.get(k))
