"""03.01.2023
A Transcriber file (.trs) has:
    - A linear structure (not by tiers)
    - A tag structure within the text/content
Note: Based on DTD v1.4 <cocoon.huma-num.fr/schemas/trans-14.dtd>.
Note: Functions starting with '_' are not meant to be called by the user.

'fromTranscriber()' should be called. It in turn calls:
    > '_checkFiles()' to determine if 'path' is a dir/file
It then calls, one or more times:
    > 'loadTRS()' to load the Transcriber file
    
Note: the 'mode' argument (kwarg) picks a method to deal with
      Event/Comment/Background tags. It is imperfect and users should
      implement their own function (see D_MODE dictionary).
Note: default values exist that the user can't control.
      Tiers without a speaker are defaulted to 'trs'.
      'meta/tier' modes have a "text_index<raw_tag>" structure.
Note: All metadata is stored in 'trs' key.
      'audio' and 'author' are stored in 'omni' (see 'readTrans()').
"""
from .Transcription import Transcription
import xml.etree.cElementTree as ETree
import os,html,re

def _checkFiles(path,ch_ext=".trs"):
    """Returns a list of '.trs' files."""
    
    def _checkFile(fpath,file,l_files):
        fi,ext = os.path.splitext(file); 
        if not ext.lower() == ch_ext:
            return
        l_files.append((fpath,fi)) 
    
    l_files = []; ch_dir = 0
    if os.path.isdir(path):        # 'path' is a directory
        for file in os.listdir(path):
            p = os.path.join(path,file)
            _checkFile(p,file,l_files)
        ch_dir = 1
    elif os.path.isfile(path):     # 'path' is a file
        file = os.path.basename(path)
        _checkFile(path,file,l_files)
    else:
        return [],-1
    return l_files,ch_dir

def _readTrans(trans,elem,d_args):
    """Get metadata from 'Trans' tag."""
    d_omni = {'audio_filename':'audio',
              'scribe':'author'}
    for k,v in elem.items():
        trans.setMeta(k,v,"trs")
        if k in d_omni:
            trans.setMeta(d_omni[k],v)
def _readTopics(trans,elem,d_args):
    """Fills a dict' of topics from the 'Topics' tag."""
    for sub in elem.iter('Topic'):
        d_args['d_top'][sub.get('id')] = sub.get('desc')
def _readSpeakers(trans,elem,d_args):
    """Adds speakers from the 'Speakers' tag.
    Speaker key is from 'name' by default, 'id' if 'name' doesn't exist."""
    for sub in elem.iter('Speaker'):
        name = sub.get('name') if 'name' in sub.keys() else sub.get('id')
        trans.addSpk(name,sub.attrib)
        d_args['d_spk'][sub.get('id')] = name
def _readSection(trans,elem,d_args):
    """Adds metadata to segments of the section."""
    def _chSegTime(s,tier):
        if not tier.elem:
            return -1
        sn,si,seg = tier.getTime(s,det=True)
        if si >= 0:
            return si
        d1,d2 = s-tier.elem[0].start,s-tier.elem[-1].start
        d1 = d1*-1 if d1 < 0 else d1
        d2 = d2*-1 if d2 < 0 else d2
        if d1>d2:
            for a in range(len(tier)-1,-1,-1):
                seg = tier.elem[a]
                if seg.start < s:
                    si = a+1; break
        else:
            for a in range(len(tier)):
                seg = tier.elem[a]
                if seg.start > s:
                    si = a; break
        if si >= len(tier):
            return -1
        else:
            return si
    
    typ,top = elem.get('type'),elem.get('topic')
    s,e = float(elem.get('startTime',"-1.")),float(elem.get('endTime',"-1."))
    desc = d_args['d_top'].get(top)
    if (not typ) or s < 0.: # Nothing to add
        return
    for tier in trans: # For all tiers...
        si = _chSegTime(s,tier)
        if si < 0:
            continue
        for a in range(si,len(tier)): # For all segs' in that section...
            seg = tier.elem[a]
            if seg.end > e:
                break
            seg.setMeta('type',typ,'trs')
            if desc:
                seg.setMeta('desc',desc,'trs')
def _toText(sub,sub_txt,ntxt,i,seg,l_trs):
    """Adds tag's 'desc' to segment content."""
    return ntxt+" "+sub.get('desc',"")+" ",l_trs
def _toTier(sub,sub_txt,ntxt,i,seg,l_trs):
    """Adds tag to another tier."""
    cont = f"{i}{sub_txt}"
    tag = sub if isinstance(sub,str) else sub.tag
    if seg:
        tier = seg.struct; trans = tier.struct
        nname = tier.name+"[trs]"
        ntier = trans.getName(nname); nseg = None
        if not ntier:
            ntier = trans.create(tier.index()+1,nname,-1.,-1.)
            nseg = ntier.create(-1,"",seg.start,seg.end,cont)
            return ntxt,l_trs
        if ntier.elem and ntier.elem[-1].end < seg.start:
            nseg = ntier.create(-1,"",seg.start,seg.end,cont)
        else:
            ntier.elem[-1].content = (ntier.elem[-1].content+cont)
    else:
        l_trs.append((tag,cont))
    return ntxt,l_trs
def _toMeta(sub,sub_txt,ntxt,i,seg,l_trs):
    """Adds tag to segment metadata."""
    cont = f"{i}{sub_txt}"
    tag = sub if isinstance(sub,str) else sub.tag
    if seg:
        seg.setMeta(tag,cont,"trs")
    else:
        l_trs.append((tag,cont))
    return ntxt,l_trs
D_MODE = {'text':_toText,'tier':_toTier,'meta':_toMeta}
def _readTurn(trans,elem,d_args):
    """Adds segments from the 'Turn' tag.
    Handles sub-tags ('Who','Sync','Comment','Event','Background')."""
    
    def _endSeg(seg,sf,cont):
        if seg:
            seg.end = sf
            seg.content = cont if cont else seg.content
    def _getWho(sub,l_spk,seg,s,e,ntxt):
        """Changes the tier."""
        if isinstance(sub,int):
            spk = l_spk[sub]
        else:
            spk = l_spk[int(sub.get('nb'))-1]
        tier = trans.getName(spk) # new tier
        if not tier:
            tier = trans.create(-1,spk,-1.,-1.,"")
        if seg:
            _endSeg(seg,e,ntxt); ntxt = ""
        seg = tier.create(-1,"",s,e,"")
        return tier,seg,ntxt
    def _getSync(sub,tier,seg,s,e,ntxt):
        s = float(sub.get('time'))
        if seg and s > seg.start:
            _endSeg(seg,s,ntxt); ntxt = ""
            seg = tier.create(-1,"",s,e,"")
        elif (not seg) and tier:
            seg = tier.create(-1,"",s,e,"")
        return seg,s,ntxt
    
    s,e = float(elem.get('startTime',-1.)),float(elem.get('endTime',-1.))
    l_spk = elem.get('speaker',"")
    l_spk = l_spk.split(" ") if " " in l_spk else [l_spk]
    l_subs = [sub for sub in elem.iter() if not sub.tag == "Turn"]
        # get tag content as text
    txt = html.unescape(ETree.tostring(elem).decode('utf_8'))
    txt = txt.split(">",1)[1].rsplit("</",1)[0]
    txt = re.sub('\r?\n( |\t)*','',txt)
        # Parse
    tier,seg,ntxt,nsub = None,None,"",""
    if len(l_spk) <= 1: # No 'Who', single speaker
        if not l_spk[0]: # No speaker, generate default tier
            l_spk = ["trs"]
        tier,seg,ntxt = _getWho(0,l_spk,seg,s,e,ntxt)
    l_trs,oseg = [],None
    if seg:
        oseg = seg
    s_incr,e_incr,incr = 0,0,0
    si,ch_txt = 0,True
    for a,char in enumerate(txt):
        if char == "<":
            sub = l_subs[si]; si += 1; ch_txt = False
            s_incr = a; nsub = "<"
        elif char == ">":
            len_sub = a-s_incr+1; s_incr = s_incr-incr # text increment
            incr = incr+len_sub
            if sub.tag == "Who": # change of tier
                tier,seg,ntxt = _getWho(sub,l_spk,seg,s,e,ntxt)
                if not oseg:
                    oseg = seg
            elif sub.tag == "Sync": # change of segment
                seg,s,ntxt = _getSync(sub,tier,seg,s,e,ntxt)
                if not oseg:
                    oseg = seg
            else: # Transcriber tag (see 'mode')
                f2 = D_MODE.get(d_args['mode'])
                if f2:
                    ntxt,l_trs = f2(sub,nsub,ntxt,s_incr,seg,l_trs)
            ch_txt = True; nsub = ""
        elif ch_txt:
            ntxt = ntxt+char
        else:
            nsub = nsub+char
    _endSeg(seg,e,ntxt)
    if l_trs and oseg: # Last Transcriber tag check (tags before first segment)
        f2 = D_MODE.get(d_args['mode'])
        for tag,cont in l_trs:
            i,nsub = cont.split(";")
            ntxt,l_trs = f2(tag,nsub,"",i,oseg,l_trs)
D_TAG = {'Trans':_readTrans,'Topics':_readTopics,'Speakers':_readSpeakers,
         'Section':_readSection,'Turn':_readTurn}

def loadTRS(path,name="",mode="text"):
    """Main function to load a given TRS file.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes encoding (and 'name') is known."""
    
        # New Transcription instance
    trans = Transcription(name=name,metadata={})
    root = None; b_root = False
    d_args = {'mode':mode,
              'd_top':{},'d_spk':{}}
    for event, elem in ETree.iterparse(path, events=("start","end")):
        if not b_root: # Find root for operation (cleaning)
            root = elem; b_root = True
        elif event == "end":
            f = D_TAG.get(elem.tag)
            if f:
                f(trans,elem,d_args)
                par = root.find(f".//{elem.tag}/..")
                if par:
                    par.remove(elem)
    trans.setBounds()
    trans.renameSegs()
    return trans
def fromTranscriber(path,**args):
    """Imports one or more TRS(s).
    ARGUMENTS:
    - path          : (str) A full path to either a file or a directory.
    - mode          : (str) How to handle tags in content
    RETURNS:
    - trans/l_trans : (pntr/list) Either a Transcription or a list of
                                  Transcriptions.
    Note: for mode, 'text' for 'desc' in content, 'tier' for new tiers
                and 'meta' for tag in segment metadata."""
    
    mode = args.get("mode","text")
        # Get files
    l_files,ch_dir = _checkFiles(path)
    if ch_dir == 1:                 # list of files
        l_trans = []
        for tup in l_files:
            l_trans.append(loadTRS(*tup,mode))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadTRS(*l_files[0],mode)