

from .Transcription import Corpus,Transcription
import os,re,html

    # Technical functions
def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
    if not encoding:    # No user-defined encoding
        return trans.meta('encoding','tech',empty="utf_8") # Check meta
    else:               # User-defined
        return encoding
def _escText(data):
    """Escapes only the text part of an ETree.tostring() result."""
    
    def interScape(s):
        """God..."""
        return s
    
    if data.endswith("/>"):                         # single tag
        l_data = data.split("\"")
        for a in range(1,len(l_data),2):
            l_data[a] = "\""+html.escape(l_data[a])+"\""
        res = ""
        for d in l_data:
            res = res+d
        return res+"\n"
    elif not ">" in data:                           # no tag
        return html.escape(data)
        # Tag with text
    prev,core = data.split(">",1); prev = prev[1:]
    core = core.strip("\n ")
    prev = interScape(prev)
    if core:
        core,next = core.rsplit("<",1); next = next.rsplit(">",1)[0]
        core = interScape(core); next = interScape(next)
        return "<"+prev+">"+core+"<"+next+">\n"
    else:
        return "<"+prev+">\n"
    return 
l_level = ['TEXT','S','W','M']

    # Writing functions
def _chLvls(trans,l_tiers):
    """Attributes tiers to levels.
    Note: auto-detect relies on tier names following 'LVL-code'."""
    
    def nDecode(code):
        """Turns 'LVL-code' into 'lvl','type' and 'lang'.
        Note: 'code' is 'lang' (TRANSL) or an increment '[0-9]+' (FORM)."""
        lvl,lang = code.split("-",1); typ = "TRANSL"
        if re.match("[0-9]+",lang):
            typ = "FORM"
        return lvl,typ,lang
    def fillDict(d_lvl,lvl,typ,lang,tier):
        """Add information to both tier and 'd_lvl'."""
        tier.setMeta("level",lvl,"tech"); tier.setMeta("type",typ,"tech")
        tier.setMeta("pos",0,"tech"); tier.setMeta("len",len(tier),"tech")
        tier.setMeta("time",-1.,"tech")
        if typ == "TRANSL":
            tier.setMeta("lang",lang,"tech")
        if lvl in d_lvl:
            d_lvl[lvl].append(tier)
        else:
            d_lvl[lvl] = [tier]
    def tierDefined(d_lvl):
        """Rely on tier names, assume they follow 'LVL-code'."""
        for tier in trans:
            if not "-" in tier.name: # Invalid information
                continue
            lvl,typ,lang = nDecode(tier.name)
            fillDict(d_lvl,lvl,typ,lang,tier)
    def userDefined(d_lvl,l_tiers):
        """User provided a list of (tier_name,'LVL-code')."""
        for name,code in l_tiers:
            tier = trans.getName(name)
            if (not "-" in code) or (not tier): # Invalid information
                continue
            lvl,typ,lang = nDecode(code)
            fillDict(d_lvl,lvl,typ,lang,tier)

    d_lvl = {}
    if l_tiers:
        userDefined(d_lvl,l_tiers)
    else:
        tierDefined(d_lvl)
    return d_lvl
l_tattr = ['id','xml:lang','author','kindOf']
def _writeAttr(obj,tab,div="pangloss"):
    """Writes tag and attribute for a given segment."""
    stag = obj.meta("type","tech")
    tmp = tab+"<"+stag
    ch_n,ch_l = False,False
    for k,v in obj.iterMeta(div):
        if k in l_tattr:
            tmp = tmp+" "+k+"=\""+html.escape(v)+"\""
            if k == "kindOf":
                ch_n = True
            elif k == "xml:lang":
                ch_l = True
    if (not ch_n) and stag == "FORM" and obj.checkMeta("name"):
        tmp = tmp+" kindOf=\""+html.escape(obj.meta("name"))+"\""
    if (not ch_l) and stag == "TRANSL" and obj.checkMeta("lang"):
        tmp = tmp+" xml:lang=\""+html.escape(obj.meta("lang"))+"\""
    return tmp
def _writeAudio(tab,ts,te):
    """Writes AUDIO tag."""
    return tab+"<AUDIO start=\"{:.04f}\" end=\"{:.04f}\" />\n".format(ts,te)
def _writeNOTE(obj,tab):
    """Writes NOTEs after a given segment (or at Trans' level)."""
    tmp = ""
    for k,l_v in obj.iterMeta("pangloss",ch_list=True):
        if not k == "NOTE":
            continue
        for v in l_v:
            tmp = tmp+tab+_escText(v)
    return tmp
def _writeSeg(tier,seg,tab):
    """Writes a Segment (FORM/TRANSL) and its NOTEs."""
    tmp = _writeAttr(tier,tab)+(">"+html.escape(seg.content)+"</"+
                               tier.meta("type","tech")+">\n")
    tmp = tmp+_writeNOTE(seg,tab)
    return tmp
def _writeHeader(trans,d_lvl,l_lvl,tab):
    """Returns the header and footer of the file."""
    
    def fillHeader(tab):
        h = tab+"<HEADER"
        tmp = ">\n"; tab = tab+"\t"
        l_h = [("TITLE","name"),("SOUNDFILE","audio")]
        for Pn,On in l_h:
            if trans.checkMeta(Pn,div="pangloss"):
                for val in trans.meta(Pn,"pangloss",ch_list=True):
                    tmp = tmp+tab+_escText(val)
            elif trans.checkMeta(On):
                for val in trans.meta("name",ch_list=True):
                    tmp = tmp+tab+"<"+On+">"+html.escape(val)+"</"+On+">\n"
        tab = tab[:-1]
        if tmp == ">\n":
            tmp = ""
        else:
            tmp = tmp+tab+"</HEADER>\n"
        return h+tmp

        # header
    mtag= ""; header = ""
    if not l_lvl or len(l_lvl) < 2:                     # (not enough levels?)
        return "",""
    if (l_lvl[0] == "WORDLIST") or (not "S" in d_lvl):
        mtag = "WORDLIST"
    else:
        mtag = "TEXT"
    trans.setMeta("type",mtag,"tech")
    header = header+_writeAttr(trans,tab)+">\n"; tab = tab+"\t"
    header = header+fillHeader(tab)                     # HEADER
    header = header+_writeNOTE(trans,tab)               # Trans' NOTEs
        # footer
    footer = ""; l_top = d_lvl.get(l_lvl[0])
    if not l_top:                                       # No top tier
        return header,(tab[:-1]+"</"+mtag+">\n")
    for tier in l_top:                                  # Write top Segments
        if not tier.elem:
            continue
        footer = footer+_writeSeg(tier,tier.elem[0],tab)
    footer = footer+(tab[:-1]+"</"+mtag+">\n")
        # Remove top level
    return header,footer,tab
def _writeTiers(trans,d_lvl,l_lvl,tab):
    """Writes each level and its sub-level.
    ARGUMENTS:
    - 'trans'       : (pntr) transcription
    - 'd_lvl'       : (dict) list of tiers per level.
    - 'l_lvl'       : (list) list of levels
    - 'tab'         : (str) a set of '\t'.
    Note: We assume all tiers from a given level share the same time codes."""
    
    def _iterLTiers(l_tiers):                       # iterator
        """Iterates over a given level's tiers."""
        for tier in l_tiers:
            pos = tier.meta("pos","tech")
            if pos >= tier.meta("len","tech"):
                continue
            yield tier,pos,tier.elem[pos]
    def getEarliest(l_tiers):                       # find start/end times
        """Returns the earliest start/end times."""
        s,e = -1.,-1.
        for tier,pos,seg in _iterLTiers(l_tiers):
            if s < 0. or seg.start < s:
                s,e = seg.start, seg.end
        return s,e
    def setLTimes(trans,l_lvl,d_lvl):               # setup 'll_times'
        """Set 'l_times' (we need the earliest start/end times per level)."""
        ll_times = [[trans.start,trans.end,True]]
        lv = len(l_lvl); i_lvl = 1
        for a in range(1,lv):           # Get time codes per level
            lvl = l_lvl[a]; l_tiers = d_lvl[lvl]
            s,e = getEarliest(l_tiers)
            ll_times.append([s,e,False]) # Add to 'l_times'
        return ll_times,lv,i_lvl
    def upPos(l_tiers,s,e):                         # increment 'pos'
        """Increments the 'pos' metadata in 'tech'."""
        for tier,pos,seg in _iterLTiers(l_tiers):
            while tier.elem[pos].start <= s:
                pos += 1
                if pos >= tier.meta("len","tech"):
                    tier.setMeta("pos",pos,"tech"); break
            tier.setMeta("pos",pos,"tech")
        return getEarliest(l_tiers)
    def writeStart(txt,tag,tab,seg,id,i_lvl,ll_times):
        """Opening level with tag."""
        seg.setMeta("type",tag,"tech"); tmp = ""
        tmp = tmp+_writeAttr(seg,tab,"pangloss_sub")
        if not "id=" in tmp:
            tmp = tmp+" id=\""+tag+str(id)+"\""; id+=1
        txt = txt+tmp+">\n"; tab = tab+"\t"
        ll_times[i_lvl][2] = True
        return txt,tab,id,i_lvl,ll_times
    def writeEnd(txt,tag,tab,i_lvl,ll_times):
        """Closing level with tag."""
        tab = tab[:-1]; txt = txt+tab+"</"+tag+">\n"
        ll_times[i_lvl][2] = False
        return txt,tab,i_lvl,ll_times
    def allSegs(txt,l_tiers,s,e,ps,ch,tab,id,i_lvl,ll_times):
        """Writes FORM/TRANSL/NOTE/AREA for a given time code."""
        for tier,pos,seg in _iterLTiers(l_tiers):
            if not ch:                          # Start of level
                txt,tab,id,i_lvl,ll_times = writeStart(txt,lvl,tab,seg,id,
                                                       i_lvl,ll_times)
                txt = txt+_writeAudio(tab,s,e); ch = True
            txt = txt+_writeSeg(tier,seg,tab)
        return txt,tab,id,i_lvl,ll_times
    
        # Variables
    txt = ""; ll_times,lv,i_lvl = setLTimes(trans,l_lvl,d_lvl)
    id = 0
        # Main loop
    while i_lvl >= 1:                           # From ashes to ashes...
            # Get level information
        lvl = l_lvl[i_lvl]; l_tiers = d_lvl[lvl]# level and tiers
        ps,pe,pch = ll_times[i_lvl-1]           # Parent start-end times
        s,e,ch = ll_times[i_lvl]                # start-end times
            # Checks
        if ch:                                  # End of level
            txt,tab,i_lvl,ll_times = writeEnd(txt,lvl,tab,i_lvl,ll_times)
            s,e = upPos(l_tiers,s,e); ch = False
            ll_times[i_lvl] = [s,e,ch]
        if s < 0. or s >= pe-0.001:                   # Go back one level
            i_lvl = i_lvl-1; continue
            # Write segments
        txt,tab,id,i_lvl,ll_times = allSegs(txt,l_tiers,s,e,ps,ch,tab,id,
                                            i_lvl,ll_times)
        if i_lvl+1 < lv:                   # Check next level
            i_lvl += 1
    return txt
              
def saveCRDO(txt,trans,l_tiers,l_lvl,tab):
    """Exports a single Transcription into an xml (CRDO) file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - encoding      : (str) The xml file encoding.
    RETURNS:
    - txt           : (str) Content for that file."""
    
    ntrans = trans.copy()                           # We use a copy from there
    ntrans.fixOverlaps()
    d_lvl = _chLvls(ntrans,l_tiers)                 # We get our tiers
    h,f,tab = _writeHeader(ntrans,d_lvl,l_lvl,tab)  # Get header/footer
    b = _writeTiers(ntrans,d_lvl,l_lvl,tab)         # Get sub-levels
    return h+b+f
    # Main function
def toPangloss(path,trans,**args):
    """Exports one or more CRDO files (Pangloss, '.xml').
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - encoding      : (str) The file encoding.
    - l_tiers       : (list<tpl<str>>) File structure in tuples of strings
                                       (tier.name,code)
    - l_level       : (list<str>) Level structure
    RETURNS:
    - Creates the xml(s) at 'path' from 'trans'.
    Note: Creates a copy for each Transcription while exporting.
    Note: 'l_tiers' levels are 'S/W/M(/P)'. Tiers not included are dropped.
          Segments that don't fit are dropped."""
    
    def chPath(p,enc):
        if os.path.isdir(p):                        # If it's a directory
            p = os.path.join(p,trans.name+".xml")   # Use 'trans.name'
        enc = _chEncoding(trans,enc)                # Encoding
        return open(p,'w',encoding=enc)
    
        # Args
    encoding = args.get('encoding')     # file encoding (for all files)
    l_tiers = args.get('l_tiers')       # tiers to use (for S/W/M...)
    l_lvl = args.get('l_level',l_level) # CRDO levels
        # Overload
    ch = d_load.get(type(trans))
    if ch:
        f = chPath(path,encoding); txt = ""; tab = ""
        if ch > 1:                                  # Corpus/list
            txt = "<ARCHIVE>"; tab = "\t"
            for tr in trans:                        # For each Transcription
                txt = saveCRDO(txt,tr,l_tiers,l_lvl,tab)
            txt = txt+"</ARCHIVE>\n"
        else:                                       # Single Transcription
            txt = saveCRDO(txt,trans,l_tiers,l_lvl,tab)
        f.write(txt); f.close()                     # Write
    else:
        raise KeyError("First argument must be of type 'Transcription/"+
                       "/Corpus/list'.")
d_load = {Transcription:1,Corpus:2,list:3}