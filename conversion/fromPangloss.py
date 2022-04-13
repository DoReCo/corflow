""" 11/03/2022
A Pangloss (CRDO) file <cocoon.huma-num.fr/exist/crdo/meta/
cocoon-49aefa90-8c1f-3ba8-a099-0ebefc6a2aa7> has:
    - a series of 'levels' (XML nodes) 'S,W,M,...'
    - either ARCHIVE, TEXT or WORDLIST as root
    
'fromPangloss()' should be called. It in turn calls:
    > '_checkFiles()' to determine if 'path' is a dir/file
It then calls, one or more times:
    > 'loadPangloss()' to load the CRDO file
    
Note: if root is "ARCHIVE", returns a 'Corpus' instance.
      Else ("TEXT/WORDLIST"), returns a 'Transcription'.
Note: FORM/TRANSL tags are turned into Segments.
      Tier name for a FORM is the level (S,W,...), dash and increment.
      Tier name for a TRANSL is the level (S,W,...), dahs and 'xml:lang'.
Note: a FORM will have a 'name' in 'omni' if 'kindOf' attribute.
      see 'd_omni' for Tier 'omni' metadata.
Note: 'TEXT' (and technically 'WORDLIST') is its own level.
Note: 'fromPangloss()' stores levels in 'l_subs'. Aside from 'TEXT',
      who is hard-coded in '_readRoot()', 'l_subs' can be freely edited.
Note: Tiers/Segments are time-aligned but left independent.
Note: NOTE/FOREIGN in text are left as is,
      NOTE/AREA as metadata is returned as block of texts (see 'strIt').
Note: Conteneur.metadata uses 'pangloss' and 'pangloss_sub' keys.
"""
from .Transcription import Corpus,Transcription
import xml.etree.cElementTree as ETree
import os,html

    # Technical functions
def _checkFiles(path,ch_ext=".xml"):
    """Returns a list of '.xml' files."""
    
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
d_omni = {'kindOf':'name','xml:lang':'lang'}        # 'omni' keys
l_subs = ['TEXT','S','M','W']                       # sub-levels
def _audio(el,s=-1.,e=-1.):                         # AUDIO tag
        etime = el.find("AUDIO")
        if not etime == None:
            s,e = float(etime.get('start')),float(etime.get('end'))
            el.remove(etime)
        return s,e
def strIt(el):
    return html.unescape(ETree.tostring(el).decode().rsplit("\n",1)[0])
def omniMD(obj,el,div="pangloss"):                  # Attributes
    """Fills metadata ('pangloss' div) and 'omni'."""
    for key,val in el.items():
        val = html.unescape(val)
        if key.endswith("lang"):
            key = "xml:lang"
        if not obj.checkMeta(key,div=div):
            obj.setMeta(key,val,div,-1)
            omni = d_omni.get(key)
            if omni:
                obj.setMeta(omni,val,i=-1)
def _addSeg(trans,elem,subel,s,e,incr,c):           # FORM/TRANSL
    """Deals with FORM/TRANSL by addings Segments."""

        # Establish the tier name
    nt = elem.tag+"-"+str(incr)
    if subel.tag == "TRANSL":                   # TRANSL
        for key,val in subel.items():           # get 'lang' for name
            if key.endswith("lang"):
                nt = elem.tag+"-"+str(val); ch_incr = False; break
    else:                                       # FORM (increment)
        incr += 1
        # Get/create the tier
    tier = trans.getName(nt)
    if not tier:
        tier = trans.create(-1,nt)
        tier.setMeta('incr',incr,"tech"); tier.setMeta('tag',subel.tag,"tech")
        tier.setMeta('level',elem.tag,"tech")
    omniMD(tier,subel)
        # Clean content (FOREIGN/NOTE)
    cont = ETree.tostring(subel).decode().split(">",1)[1]
    cont = html.unescape(cont.rsplit("</",1)[0])
        # Add segment
    seg = tier.create(-1,str(c),s,e,cont)
    omniMD(seg,elem,"pangloss_sub")
    c += 1
    return tier,seg,incr,c
def loopTags(trans,el,s,e,incr,c):
    """Loops over remaining NOTE/FORM/TRANSL/AREA tags."""
    
    l_notes,d_tiers = [],{}
    for sub in el:                                  # get data
        if sub.tag == "FORM" or sub.tag == "TRANSL":
            tier,seg,incr,c = _addSeg(trans,el,sub,s,e,incr,c)
            d_tiers[tier] = seg
        elif not sub.tag in l_subs:
            l_notes.append((c,sub.tag,strIt(sub)))
    return l_notes,d_tiers,incr,c
def attribNotes(trans,l_notes):
    """Assigns NOTE/AREA to Segments"""
    for c,key,val in l_notes:
        c = c-1
        for tier in trans:
            for a in range(len(tier)-1,-1,-1):
                seg = tier.elem[a]; ch = int(seg.name)
                if ch < c:              # wrong tier
                    break
                elif ch == c:           # found segment
                    seg.setMeta(key,val,'pangloss',-1); break

    # Writing functions
def _readRoot(corpus,root,el):
    """Deals with ARCHIVE, TEXT and WORDLIST tags."""
    
    def cr(co):
        if co:
            trans = co.create(metadata={})
        else:
            trans = Transcription(metadata={})
        return co,trans
    
    tr_tag = ""; sub = ""; trans = None
    if not root:
        root = el
        if el.tag == "ARCHIVE":
            corpus = Corpus()
            return root,False,corpus,trans,tr_tag,sub
    if el.tag == "TEXT":
        corpus,trans = cr(corpus); tr_tag = el.tag; sub = "S"
    elif el.tag == "WORDLIST":
        corpus,trans = cr(corpus); tr_tag = el.tag; sub = "W"
    if trans:
        omniMD(trans,el)
    return root,True,corpus,trans,tr_tag,sub
def _readHeader(trans,el):                          # HEADER
    """Reads the HEADER."""
    for sub in el.iter():
        if sub.tag == "TITLE":
            trans.setMeta('name',sub.text,i=-1)
            trans.setMeta('TITLE',strIt(sub),'pangloss',i=-1)
        elif sub.tag == "SOUNDFILE":
            audio = sub.get('href')
            trans.setMeta('audio',audio,i=-1)
            trans.setMeta('SOUNDFILE',strIt(sub),'pangloss',i=-1)
def _readSub(trans,el,c,s=-1.,e=-1.):               # S/W/M
    """Deals with S (sentences), W (words) and M (morphemes)."""
    
    def recursion(c,s,e):               # W/M tags
        """Reads the lower levels recursively. Parenting is done here."""
        d_tmp = {}; ld = 0
        for sn in l_subs:                # For 'W' and 'M' in order
            l_fsubs = el.findall(sn); lf = len(l_fsubs)
            if lf > 0:                   # Don't divide by zero
                dur = ((e-s)/lf)
            for a in range(lf):
                sa = trans._decimal(s+(dur*a))
                ea = trans._decimal(s+(dur*(a+1)))
                d_tiers,c = _readSub(trans,l_fsubs[a],c,sa,ea)
                el.remove(l_fsubs[a])
        return c

    incr = 0                        # Tier increment (deprecated)
    s,e = _audio(el,s,e)            # First we need time codes
    l_notes,d_tiers,incr,c = loopTags(trans,el,s,e,incr,c)# Then tags
    c = recursion(c,s,e)            # Then we deal with 'W/M'
    attribNotes(trans,l_notes)      # Attribute NOTE/AREA to Segments
    return d_tiers,c
def _readFooter(trans,el,c):
    """Deals with TEXT/WORDLIST, after HEADER/S/W got read."""
    incr = 0                                # Get a tier increment
    for tier in trans:
        if tier.meta("tag",div="tech") == "FORM":
            incr += 1
    incr += 1
    s,e = _audio(el,-1.,-1.); l_notes = []; oc = c  # Time codes
    l_notes,d_tiers,incr,c = loopTags(trans,el,s,e,incr,c)
    for a in range(len(l_notes)-1,-1,-1):           # Trans NOTEs
        d,key,val = l_notes[a]
        if d == oc:
            trans.setMeta(key,val,"pangloss",-1)
            l_notes.pop(a)
    attribNotes(trans,l_notes)              # Tier NOTEs
    return c
def _fixStructure(corpus,trans,name):
    """Was meant to parent tiers/segments but proves too hazardous.
    A bit of cleaning instead, then returns either 'corpus' or 'trans'."""
    
    def cleanTr(tr):
        """Gives TEXT tiers time codes, removes 'tech' dict, renames segs'."""
        s,e = -1.,-1.; tr.setBounds(allow=False)
        for tier in tr:
            if tier.meta("level","tech") == "TEXT" and len(tier) == 1:
                tier.elem[0].start = tr.start; tier.elem[0].end = tr.end
            tier.metadata.pop("tech")
        tr.renameSegs()
    if corpus:
        for tr in corpus:
            cleanTr(tr)
        corpus.name == name; corpus.setMeta("name",name)
        return corpus
    else:
        cleanTr(trans)
        trans.name = name; trans.setMeta("name",name)
        return trans
def loadPangloss(path,name=""):
    """Main function to load a given EAF file.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes encoding (and 'name') is known."""
    
        # Variables
    corpus = None; trans = None             # Corpus and transcription
    root = None; b_root = False; c = 0      # root element, test and increment
    tr_tag = ""; sub = "S"                  # "root" tag and first sub-tag
    for event, elem in ETree.iterparse(path, events=("start","end")):
        if not b_root:
            root,b_root,corpus,trans,tr_tag,sub = _readRoot(corpus,root,elem)
        elif event == "end":
            if elem.tag == sub:             # S/W/M
                _,c = _readSub(trans,elem,c); root.remove(elem)
            elif elem.tag == "HEADER":      # HEADER (TITLE/SOUNDFILE)
                _readHeader(trans,elem); root.remove(elem)
            elif elem.tag == tr_tag:        # ARCHIVE/TEXT/WORDLIST
                c = _readFooter(trans,elem,c)
                if elem in root:
                    root.remove(elem)
                b_root = False; incr = 0
    del root
    ret = _fixStructure(corpus,trans,name)
    return ret

    # Main function
def fromPangloss(path,**args):
    """Imports one or more XML(s) (Pangloss).
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
            l_trans.append(loadPangloss(*tup))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadPangloss(*l_files[0])