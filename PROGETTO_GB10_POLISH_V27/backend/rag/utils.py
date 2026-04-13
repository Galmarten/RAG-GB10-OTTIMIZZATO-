
import re

def clean_text(t:str)->str:
    t = t.replace('\r',' ')
    t = re.sub(r'\n\s*\n','\n\n',t)
    t = re.sub(r'[ \t]+',' ',t)
    return t.strip()

def chunk_text(text:str, chunk_size:int, overlap:int):
    if chunk_size<=0:
        yield text; return
    start=0; n=len(text)
    while start<n:
        end=min(n,start+chunk_size)
        yield text[start:end]
        start=end-overlap if (end-overlap)>start else end
