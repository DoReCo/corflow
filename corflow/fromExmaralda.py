"""23.01.2023
Updated script from 'fromExmaralda', Corflow v2.
No idea what version of Exmaralda this was based on.
Not tested yet but should work.

Main changes have been metadata and replacing 'ifs' with dictionaries.
(Plus tier/segment creation functions.)
'_checkTrans()' has also been heavily reworked and could cause trouble.

/!\ segment metadata is stored directly in 'omni' subdivision!
"""
from .Transcription import Transcription, Tier
import xml.etree.cElementTree as ETree
import os,html

def _checkFiles(path,ch_ext=".exb"):
    """Returns a list of '.exb' files."""
    
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

def _readMeta(trans,elem,d_timeorder,count):
    """Adds transcription metadata.
    'name' and 'audio' may be set in 'omni' subdivision.
    'ud_meta-information' doesn't conserve tag names in 'exb' subdivision."""
    
    def _addMeta(el,trans):
        if not el.text:
            return
        trans.setMeta(el.tag,el.text,"exb")
        if el.txt == "transcription-name":
            trans.setMeta("name",el.text)
    def _addRef(el,trans):
        url = el.get('url')
        if url:
            trans.setMeta(el.tag,url,"exb")
            base = os.path.basename(url)
            trans.setMeta("audio",base)
    def _addUD(el,trans):
        for e in el:
            if not ("attribute-name" in e.attrib and e.text):
                continue
            trans.setMeta(e.get('attribute-name'),e.text,"exb")
    d_meta = {'project-name':_addMeta,
              'transcription-name':_addMeta,
              'referenced-file':_addRef,
              'ud_meta-information':_addUD,
              'comment':_addMeta,
              'transcription-convention':_addMeta}
    for el in elem:
        g = d_meta.get(el.tag)
        if g:
            g(el,trans)
    return count
def _readSpeakers(trans,elem,d_timeorder,count):
    """Adds speaker metadata."""
    
    def _addMeta(el,d_vals):
        if not el.text:
            return
        if el.tag in d_vals:
            d_vals[el.tag].append(html.unescape(el.text))
        else:
            d_vals[el.tag] = [html.unescape(el.text)]
    def _addSex(el,d_vals):
        if "value" in el.attrib:
            d_vals['sex'] = html.unescape(el.get('value'))
        elif el.text:
            d_vals['sex'] = html.unescape(el.text)
    def _addLang(el,d_vals):
        for e in el:
            lang = e.get('lang')
            if not lang:
                continue
            if el.tag in d_vals:
                d_vals[el.tag].append(html.unescape(lang))
            else:
                d_vals[el.tag] = [html.unescape(lang)]
    def _addUD(el,d_vals):
        for e in el:
            if "attribute-name" in e.attrib and e.text:
                d_vals[e.get("attribute-name")] = html.unescape(e.text)
    d_meta = {'abbreviation':_addMeta,
              'sex':_addSex,
              'languages-used':_addLang,
              'l1':_addLang,
              'l2':_addLang,
              'ud-speaker-information':_addUD,
              'comment':_addMeta}
    id = ""; lang = ""
    for spk in elem:
            # Get the ID (or we can't create the speaker)
        id = spk.get('id')
        if not id:
            id = spk.get('abbreviation')
        if not id:
            continue
            # Add the speaker
        d_vals = {}
        for el in spk:
            g = d_meta.get(el.tag)
            if g:
                g(el,d_vals)
        spk = trans.addSpk(id,d_vals=d_vals)
    return count
def _readTimeline(trans,elem,d_timeorder,count):
    """Support function to fill the 'timeorder' list."""
    
    for tli in elem:
        if "time" in tli.attrib:
            d_timeorder[tli.get("id")] = float(tli.get("time"))
        else:
            d_timeorder[tli.get("id")] = -1.
    return count
def _readTier(trans,elem,d_timeorder,count):
    """Support function to fill the tiers.
    
    Note: category and type.
    category    :   'v', 'de', 'sup', 'nv' (verbal, german, suprasegmental, 
                                            non-verbal)
    type        :   't', 'd', 'a' (transcription, non-verbal, annotation)
    There should be only one 't' per speaker."""
    
    def _readSegment(tier,el,count):
        # segment time boundaries
        s,e = -1.,-1.
        for k,v in el.attrib.items():
            if k == "start":
                s = d_timeorder[v]
            elif k == "end":
                e = d_timeorder[v]
            # segment metadata
        d_smeta = {}
        for e in el:
            if (e.tag == "ud-information" and
                "attribute-name" in e.attrib and e.text):
                d_smeta[e.get("attribute-name")] = html.unescape(e.text)
                el.remove(e)
            # id and content
        id = "a"+str(count); count += 1
        l_txt = []
        for txt in el.itertext():
            l_txt.append(txt)
        cont = html.unescape("".join(l_txt))
        seg = tier.create(-1,"",s,e,cont,tier,metadata=d_smeta.copy())
        return count
    
        # tier
        ## We don't check the speaker, category, type
    tier = trans.create(-1,"",trans.start,trans.end,struct=trans)
    for k,v in elem.attrib.items():
        tier.setMeta(k,html.unescape(v),"exb")
        if k == "display-name":
            tier.name = html.unescape(v)
        # segments
    cont = ""; id = ""; s_meta = {}
    for el in elem:
        if el.tag == "ud-tier-information": # additional tier metadata
            for e in el:
                k = e.get('attribute-name')
                if k and e.text:
                    tier.setMeta(k,html.unescape(e.text))
        else:
            count = _readSegment(tier,el,count)
    return count
D_TAG = {"meta-information":_readMeta,
         "speakertable":_readSpeakers,
         "common-timeline":_readTimeline,
         "tier":_readTier}
def _checkTrans(trans):
    """Support function to finalize the transcription.
    1. Establish a structure using speakers (and types).
    2. Deal with missing time boundaries."""
    
        # Clean the name
    for tier in trans:
        if tier.meta("category"):
            c = "["+tier.meta('category')+"]"; l = len(c)*-1
            if tier.name.endswith(c):
                tier.name = tier.name[:l]
        # Get speakers
    d_spk = {}
    for tier in trans: ## First we sort the tiers by speakers
        spk = tier.meta("speaker")
        if not spk:
            continue
        if spk in d_spk:
            d_spk[spk].append(tier)
            
        else:
            d_spk[spk] = [tier]
    for spk,l_tiers in d_spk.items(): ## Then we parent
        trans.setSpk(spk,"tiers",l_tiers)
        test = False
        for tier in l_tiers:
            if not (tier.meta("type") == "t"):
                continue
            for ctier in list:
                if tier == ctier:
                    continue
                ctier.setParent(tier); test = True
        if test == True:
            continue
        ptier = None
        for a,tier in enumerate(l_tiers):
            if not ptier:
                ptier = tier; continue
            tier.setParent(ptier)
    del d_spk
    
        # Get subd
        ## In case some time boundaries lacked a value
    l_segs = []
    for tier in trans:
        l_segs.clear()
        for a,seg in enumerate(tier):
            s,e = seg.start,seg.end
            if e < 0. or s < 0.:
                l_segs.append(seg)
            if l_segs and e > 0.:
                tier._split(l_segs,(l_segs[0].start,e))
                l_segs.clear()

def loadEXB(path,name=""):
    """Main function to load a given EXB file.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes encoding (and 'name') is known."""

        # New Transcription instance
    trans = Transcription(name=name,metadata={})
    root = None
    d_timeorder = {}; count = 0 # count is for segment id, increment
    
    b_root = False
    for event, elem in ETree.iterparse(path, events=("start","end")):
        if not b_root:
            root = elem
            b_root = True; continue
        elif event == "end":
            if elem.tag == "tier":
                l_ev = elem.findall('event'); s = "None"
                if l_ev:
                    s = l_ev[-1].get('start')
                print(elem.tag,elem.get('id'),len(l_ev),s)
            f = D_TAG.get(elem.tag)
            if f:
                count = f(trans,elem,d_timeorder,count)
                par = root.find(f".//{elem.tag}/..")
                if par and elem in par:
                    par.remove(elem)
    del root; del d_timeorder
        # A series of checks
    _checkTrans(trans)
    return trans
def fromExmaralda(path,**args):
    """Imports one or more EXB(s).
    ARGUMENTS:
    - path          : (str) A full path to either a file or a directory.
    RETURNS:
    - trans/l_trans : (pntr/list) Either a Transcription or a list of
                                  Transcriptions."""
    
        # Get files
    l_files,ch_dir = _checkFiles(path)
    if ch_dir == 1:                 # list of files
        l_trans = []
        for tup in l_files:
            l_trans.append(loadEXB(*tup))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadEXB(*l_files[0])