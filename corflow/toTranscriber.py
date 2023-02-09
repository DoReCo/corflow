"""23.01.2023
A Transcriber file (.trs) has:
    - A linear structure (not by tiers)
    - A tag structure within the text/content
Note: Based on DTD v1.4 <cocoon.huma-num.fr/schemas/trans-14.dtd>.
Note: Functions starting with '_' are not meant to be called by the user.

'toTranscriber()' should be called.
The header is handled by '_writeHeader()', the body by '_writeEpisode()'.
Each segment of each tier contains its topic, retrieved by '_getTopics()'.
In-content tags can be retrieved with '_byTier()' or '_byMeta()'.

Note: the 'mode' argument (kwarg) picks a method to deal with
      Event/Comment/Background tags. It is imperfect and users should
      implement their own function (see D_MODE dictionary).
Note: 'trans' metadata is limited by 'trs' subdivision or audio/author.
      'speaker' metadata is limited by L_SPKATTRIB.
"""
from .Transcription import Corpus,Transcription,Tier
import os,html

L_SPKATTRIB = ['check','type','dialect','accent','scope'] # speaker attributes

def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
        # No user-defined encoding
    if not encoding:
            # Check metadata for one
        return trans.meta('encoding','tech',empty="utf_8")
    else:
        return encoding
def _wA(k,v):
    """Add tag attribute."""
    return " {}=\"{}\"".format(k,v)
def _getTopics(trans,l_segs,dflt="report"):
    """Returns a list of topics with all information."""
    toptier = Tier("sections",trans.start,trans.end,"")
    otyp,odesc,s = "","",-1
    for seg in l_segs: # check all segments in order
        typ,desc = seg.meta('type','trs'),seg.meta('desc','trs')
        if ((not typ) or 
            (typ == otyp and desc == odesc) or (seg.start == s)): # continuity
            continue
        id = "to{}".format(len(toptier)+1)
        cont = f"{id};{typ};{desc}"; ch_wr = False
        if toptier.elem:
            toptier.elem[-1].end = seg.start
        toptier.create(-1,"",seg.start,seg.end,cont)
        otyp = typ; odesc = desc; s = seg.start
    if len(toptier) == 0:
        toptier.create(-1,"",trans.start,trans.end,f"to0;{dflt};")
    return toptier
def _writeHeader(f,trans,enc,l_segs):
    """Writes xml/DOCTYPE, 'Trans' start and Topics/Speakers."""
    def _writeTransStart():
        txt = "<Trans" # 'Trans' tag start
        if 'trs' in trans.metadata: # ('trs' metadata)
            for k,v in trans.iterMeta("trs"):
                txt = txt+_wA(k,v)
        else: # ('omni' metadata)
            audio,author = trans.meta("audio"),trans.meta("author")
            if audio:
                txt = txt+_wA("audio_filename",audio)
            if author:
                txt = txt+_wA("scribe",author)
        f.write(txt+">\n")
    def _writeTopics():
        txt = "\t<Topics>\n" # 'Topics' tag start
        ttier = _getTopics(trans,l_segs,"report") # Topics
        for seg in ttier:
            id,typ,desc = seg.content.split(";")
            txt = txt+"\t\t<Topic id=\"{}\" desc=\"{}\"/>\n".format(id,desc)
        f.write(txt+"\t</Topics>\n")
        return ttier
    def _writeSpeakers():
        txt = "\t<Speakers>\n"
        d_spk,d_tspk = {},trans.getSpk()
        for spk,d_vals in d_tspk.items():
            id = spk if not "id" in d_vals else d_vals["id"]
            d_spk[spk] = id
            txt = txt+"\t\t<Speaker id=\"{}\" name=\"{}\"".format(id,spk)
            for k,v in d_vals.items():
                if k in L_SPKATTRIB:
                    txt = txt+" "+_wA(k,v)
            txt = txt+"/>\n"
        f.write(txt+"\t</Speakers>\n")
        return d_spk
    enc = enc.replace("_","-")
    f.write(f"<?xml version=\"1.0\" encoding=\"{enc}\"?>\n"
            "<!DOCTYPE Trans SYSTEM \"trans-14.dtd\">\n") # static
    _writeTransStart()
    ttier = _writeTopics() # Topics
    d_spk = _writeSpeakers()
    for tier in trans: # give speaker ids to segments
        spk = tier.meta("speaker")
        if not spk and tier.name in d_spk: # tier name is 'name', get 'id'
            spk_id = d_spk.get(tier.name)
        elif spk: # found a speaker, get 'id'
            spk_id = d_spk.get(spk)
        else: # can't find id, assume it's tier name
            spk_id = tier.name
        for seg in tier:
            seg.setMeta("spk_id",spk_id,"tech")
    return ttier
def _writeTurnStart(txt,l_segs,a,s,e):
    """Writes 'Turn' start tag. Sub-function of '_writeEpisode()'."""
    seg,l_asegs = l_segs[a],[l_segs[a]]
    ta,te = seg.start,seg.end # turn start/end times
    ospk = seg.meta("spk_id","tech") # current speaker
    l_aspk = [ospk]; o = -1 # list of speakers, loop check for 'a'
    for b in range(a+1,len(l_segs)):
        aseg = l_segs[b]
        aspk = aseg.meta("spk_id","tech")
        if aspk != ospk and aseg.start >= te: # end of turn
            a = o = b-1; break
        l_asegs.append(aseg) # add segment
        if aspk not in l_aspk: # add speaker
            l_aspk.append(aspk)
        if aseg.end > te: # lengthen turn end time
            te = aseg.end
        ospk = aseg.meta("spk_id","tech") # update current speaker
    if o < 0:
        a = len(l_segs)
    aspk = " ".join(l_aspk)
    txt = txt+("\t\t\t<Turn speaker=\"{}\" startTime=\"{}\" endTime=\"{}\">"
               .format(aspk,ta,te))
    return a+1,txt,l_aspk,l_asegs
def _byTier(trans,seg):
    """Retrieves in-content tags by looking for a tname+"[trs]" tier."""
    tname = seg.struct.name
    mtier = trans.getName(tname+"[trs]")
    if not mtier:
        return
    mseg = mtier.getTime(seg.start)
    if not mseg:
        return
    l_cont = mseg.content.split(">") # each tag
    for cont in l_cont:
        if not cont:
            continue
        i,cont = cont.split("<",1) # i == index, cont == raw tag
        i = int(i)
        cont = "<"+cont+">"
        if i >= 0 and i < len(seg.content): # 'i' hopefully holds
            seg.content = seg.content[:i]+cont+seg.content[i:]
def _byMeta(trans,seg):
    """Retrieves in-content tags by looking at seg 'trs' metadata."""
    d_vals = seg.metadata.get('trs')
    if not d_vals:
        return
    for tag,val in d_vals.items():
        i,cont = val.split("<",1)
        i = int(i)
        cont = "<"+cont
        if i >= 0 and i < len(seg.content): # 'i' hopefully holds
            seg.content = seg.content[:i]+cont+seg.content[i:]
D_MODE = {'tier':_byTier,'meta':_byMeta}
def _writeTurnContent(txt,trans,l_spk,l_asegs,mode):
    """Writes 'Turn' tag content. Sub-function of '_writeEpisode()'."""
    
    owho,osync = "",-1.
    tab = "\t\t\t\t"
    for seg in l_asegs:
        f = D_MODE.get(mode) # Retrieve in-content tags
        if f:
            f(trans,seg)
        if seg.start > osync:
            txt = txt+"\n"+tab+"<Sync time=\"{}\"/>".format(seg.start)
            osync = seg.start
        who = seg.meta("spk_id","tech")
        if (len(l_spk) > 1) and (who != owho): # Handle 'Who' tag
            i = l_spk.index(who)
            txt = txt+"\n"+tab+"<Who nb=\"{}\"/>".format(i)
            owho = who
        seg.content = seg.content.replace("\t","").replace("    ","")
        txt = txt+seg.content
    return txt
def _writeEpisode(f,trans,ttier,l_segs,mode):
    """Writes 'Episode','Section's and 'Turn's."""
    txt = "\t<Episode>\n"; i = 0
    for top in ttier: # sections
        s,e = top.start,top.end
        id,typ,desc = top.content.split(";")
        txt = txt+("\t\t<Section type=\"{}\" startTime=\"{}\" endTime=\"{}\""
                   " topic=\"{}\">\n".format(typ,s,e,id))
        a = i
        while a < len(l_segs):
            if l_segs[a].start >= e:
                i = a; break
            elif mode == "tier" and l_segs[a].struct.name.endswith("[trs]"):
                a = a+1; continue
            a,txt,spk,l_asegs = _writeTurnStart(txt,l_segs,a,s,e) # Turn start
            txt = _writeTurnContent(txt,trans,spk,l_asegs,mode) # Turn content
            txt = txt+"\n\t\t\t</Turn>\n"                       # Turn end
        txt = txt+"\t\t</Section>\n"
    f.write(txt+"\t</Episode>\n</Trans>")
def saveTRS(path,trans,encoding,mode):
    """Exports a single Transcription into a TRS file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - encoding      : (str) The Transcriber file encoding.
    - mode          : (str) Where comments/background/etc might be stored.
    RETURNS:
    - Creates a TRS file at 'path' from 'trans'.
    Note: 'path' is tested here, everything else should be known.
    """
    
        # Path
    if os.path.isdir(path):                     # If it's a directory
        path = os.path.join(path,trans.name+".trs")     # Use 'trans.name'
    encoding = _chEncoding(trans,encoding)      # Encoding
    ntrans = trans.copy()                       # We use a copy from there
        # Writing
    f = open(path,'w',encoding=encoding)        # Open file
    l_segs = [seg for seg in ntrans.iterTime()] # All segs in time order
    ttier = _writeHeader(f,ntrans,encoding,l_segs) # Write header
    _writeEpisode(f,ntrans,ttier,l_segs,mode)   # Write body
    f.close()                                   # Close file
def _saveList(path,trans,encoding,mode):
    """Exports a list of / a Corpus' transcriptions into TRS files."""
    for tr in trans:
        saveTRS(path,tr,encoding,mode)

    # Main function
def toTranscriber(path,trans,**args):
    """Exports one or more TRSs.
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - encoding      : (str) The file encoding.
    - mode          : (str) Where comments/background/etc might be stored.
    RETURNS:
    - Creates the TRS(s) at 'path' from 'trans'.
    Note: Creates a copy for each Transcription while exporting."""
    
        # Args
    encoding = args.get('encoding')     # file encoding (for all files)
    mode = args.get('mode')
        # Overload
    f = d_load.get(type(trans))
    if f:
        f(path,trans,encoding,mode)
    else:
        raise KeyError("First argument must be of type 'Transcription/"+
                       "/Corpus/list'.")
d_load = {Transcription:saveTRS,Corpus:_saveList,
          list:_saveList}