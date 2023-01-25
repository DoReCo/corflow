from .Transcription import Corpus,Transcription
import os,html

    # Technical functions
def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
        # No user-defined encoding
    if not encoding:
            # Check metadata for one
        return trans.meta('encoding','tech',empty="utf_8")
    else:
        return encoding

    # Writing functions
def _writeFilDesc(ntrans,tab="\t\t"):
    ttab = tab+tab+tab
        # Transcription name
    txt = (tab+"<fileDesc>\n"+tab+"\t<titleStmt>\n"+tab+tab+
           "<title>\n"+tab+tab+"\t<desc>"+html.escape(ntrans.name)+
           "</desc>\n"+tab+tab+"</title>\n"+tab+"\t</titleStmt>\n"+
           tab+"\t<publicationStmt>\n"+tab+tab+"<distributor>corflow"
           "</distributor>\n"+tab+"\t</publicationStmt>\n")
        # Tier metadata
    if ntrans.elem:
        i = 1
        txt = txt+(tab+"\t<notesStmt>\n"+tab+tab+"<note type=\""
           "COMMENTS_DESC\">\n"+tab+tab+"\t<note "
           "type=\"lastUsedAnnotationId\">0</note>\n"+tab+tab+
           "</note>\n"+tab+tab+"<note type=\"TEMPLATE_DESC\">\n")
        for tier in ntrans: # for each tier
            pn,pi,ptier = tier.parent(det=True)
            id = "TI"+str(i); i+=1
            tier.setMeta('id',id,'tech')
            txt = txt+(tab+tab+"\t<note xml:id=\""+id+"\">\n"+ttab+
                       "<note type=\"code\">"+html.escape(tier.name)+
                       "</note>\n") # name
            if pn:  # parent
                txt = txt+(ttab+"<note type=\"parent\">"+
                           html.escape(pn)+"</note>\n")
            for k,l_v in tier.iterMeta(div="omni",ch_list=True): # omni
                for v in l_v:
                    txt = txt+(ttab+"<note type=\""+html.escape(k)+"\">"+
                               html.escape(v)+"</note>\n")
            txt = txt+(tab+tab+"\t</note>\n")
        txt = txt+(tab+tab+"</note>\n"+tab+"\t</notesStmt>\n")
        # Sound metadata
    if ntrans.meta("audio"):
        txt = txt+(tab+"\t<sourceDesc>\n"+tab+tab+"<recordingStmt>\n"+
                   tab+tab+"\t<recording>\n")
        l_audio = ntrans.meta("audio",ch_list=True)
        for audio in l_audio:
            txt = txt+(ttab+"<media mimeType=\"audio/x-wav\" url=\""+
                       html.escape(audio)+"\"/>\n")
        txt = txt+(tab+tab+"\t</recording>\n"+tab+tab+"</recordingStmt>\n"+
                   tab+"\t</sourceDesc>\n")
    else:
        txt = txt+(tab+"\t<sourceDesc></sourceDesc>\n")
    return txt+(tab+"</fileDesc>\n")
def _writeProDesc(ntrans,tab="\t\t"):
    d_spk = ntrans.getSpk(); i = 1
    l_attr = ['age','gender']
        # Setting
    txt = (tab+"<profileDesc>\n"+tab+"\t<settingDesc>\n"+tab+tab+
           "<setting xml:id=\"d0\">\n"+tab+tab+"\t<activity/>\n"+
           tab+tab+"</setting>\n"+tab+"\t</settingDesc>\n")
    if not d_spk:
        return txt+(tab+"\t<particDesc/>\n")
    else:
        txt = txt+(tab+"\t<particDesc>\n"+tab+tab+"<listPerson>\n")
        # For each speaker...
    ttab = tab+tab+tab
    for spk,d_vals in d_spk.items():
        l_tiers = d_vals.get('tiers')
        id = "SPK"+str(i); i+= 1
        txt = txt+(tab+tab+"\t<person xml:id=\""+id+"\"")   # attributes
        for k in l_attr:
            v = d_vals.get(k)
            if v:
                txt = txt+(" "+html.escape(k)+"=\""+html.escape(v)+"\"")
        txt = txt+(">\n")
        if l_tiers:                                         # tiers
            d_vals.pop('tiers')
            txt = txt+(ttab+"<altGrp mode=\"incl\">\n")
            for tier in l_tiers:
                txt = txt+(ttab+"\t<alt type=\""+
                           html.escape(tier.name)+"\"/>\n")
                tier.setMeta('spk_id',id,'tech')
            txt = txt+(ttab+"</altGrp>\n")
        if 'name' in d_vals:                                # name
            txt = txt+(ttab+"<persName>"+html.escape(d_vals['name'])+
                       "</persName>\n")
            d_vals.pop('name')
        if d_vals:                                          # omni
            txt = txt+(ttab+"<noteGrp>\n")
            for k,v in d_vals.items():
                k,v = html.escape(k),html.escape(v)
                txt = txt+(ttab+"\t<note type=\""+k+"\">"+v+"</note>\n")
            txt = txt+(ttab+"</noteGrp>\n")
        txt = txt+(tab+tab+"\t</person>\n")
    return txt+(tab+tab+"</listPerson>\n"+tab+"\t</particDesc>\n"+tab+
                "</profileDesc>\n")
def _writeEncDesc(tab="\t\t"):
    return (tab+"<encodingDesc style=\"0.9.1\">\n"+tab+
            "\t<appInfo>\n"+tab+tab+"<application ident=\"corflow.toTei\" "
            "version=\"1.0\">\n"+tab+tab+"\t<desc>Python package 'corflow'."
            "</desc>\n"+tab+tab+"</application>\n"+tab+"\t</appInfo>\n"+tab+
            "</encodingDesc>\n")
def _writeHeader(f,ntrans,encoding):
    """Writes the file header."""
    
    txt = ("<?xml version=\"1.0\" encoding=\"{}\"?>\n"      # static
           "<TEI xmlns=\"http://www.tei-c.org/ns/1.0\">\n"
           "\t<teiHeader>\n"
           .format(encoding))
    tab = "\t\t"
    txt = txt+_writeFilDesc(ntrans,tab)     # fileDesc (name,tiers,audio)
    txt = txt+_writeProDesc(ntrans,tab)     # profileDesc (speakers)
    txt = txt+_writeEncDesc(tab)            # encodingDesc (static)
    # Note: no <revisionDesc>
    f.write(txt+("\t</teiHeader>\n"))
def _writeTimeTable(f,ntrans):
    """Writes the text timeline."""
    
    def quickConv(t):
        it = int(t)
        mn,s = (it//60),(it%60)
        h,m = (mn//60),(mn%60)
        return ("{:02d}:{:02d}:{:02d}".format(h,m,s))
    
    ttable = ntrans.timetable(); tab = "\t\t"
    txt = ("\t<text>\n"+tab+"<timeline unit=\"ms\"")
    if not ttable:
        f.write(txt+("/>\n")); return
    min = ttable[0]; id,i = "T0",1
    d_timetable = {min:id}
    tmin = quickConv(min)
    txt = txt+(">\n"+tab+"\t<when absolute=\""+tmin+"\" xml:id=\"T0\"/>\n")
    for a in range(1,len(ttable)):
        ts = ttable[a]
        id = "T"+str(i); i+=1
        t = ("{:.3f}".format(ts-min)).replace('.','')
        txt = txt+(tab+"\t<when interval=\""+t+"\" since=\"T0\" xml:id=\""+
                   id+"\"/>\n")
        d_timetable[ts] = id
    f.write(txt+(tab+"</timeline>\n"))
    return d_timetable,id
def _writeBody(f,ntrans,d_timetable,id):
    """Writes the body."""
    
    def nextSeg(l_par):
        seg,p = None,-1
        for b,tpl in enumerate(l_par):
            par,pos,max = tpl
            if pos < 0:
                continue
            elif not seg or par.elem[pos].start < seg.start:
                seg = par.elem[pos]; p = b
        if seg:
            par,pos,max = l_par[p]
            pos = pos+1
            if pos >= max:
                pos = -1
            l_par[p] = (par,pos,max)
        return seg
    
    tab,ttab,i = "\t\t","\t\t\t\t",0
    txt = (tab+"<body>\n"+tab+"\t<div subtype=\"d0\" type=\"Situation\">\n"+
           tab+tab+"<head>\n"+tab+tab+"\t<note type=\"start\">#T0</note>\n"+
           tab+tab+"\t<note type=\"end\">#"+id+"</note>\n"+tab+tab+
           "</head>\n")
    l_par = ntrans.getTop()             # get top tiers
    for a,par in enumerate(l_par):
        l_par[a] = (par,0,len(par))
    while True:                         # for each segment
        seg = nextSeg(l_par)
        if not seg:
            break
        tier = seg.struct
        id = "a"+str(i); i+=1; seg.setMeta("id",id,"tech")
        s,e = d_timetable[seg.start],d_timetable[seg.end]
        d_csegs = seg._childDict(seg.allChildren())
        for ctier,l_csegs in d_csegs.items():    # assign ids
            for cseg in l_csegs:
                id = "a"+str(i); i+=1
                cseg.setMeta("id",id,"tech")
            # Write main segment
        n = ("{}<annotationBlock xml:id=\"{}\" who=\"{}\" "
             .format(ttab,seg.meta("id","tech"),
                     html.escape(tier.name)))
        if tier.meta('spk_id','tech'):
            n = n+("ana=\"#"+tier.meta('spk_id','tech')+"\" ")
        n = n+("start=\"#"+s+"\" end=\"#"+e+"\">\n"+ttab+"\t<u")
        if seg.content:
            n = n+(">\n"+ttab+tab+"<seg>"+html.escape(seg.content)+"</seg>\n"+
               ttab+"\t</u>\n")
        else:
            n = n+("/>\n")
        for ctier,l_csegs in d_csegs.items():    # for each child segment
            n = n+(ttab+"\t<spanGrp type=\""+html.escape(ctier.name)+"\">\n")
            for cseg in l_csegs:
                pseg = cseg.parent()
                s,e = d_timetable[cseg.start],d_timetable[cseg.end]
                cid,pid = cseg.meta("id","tech"),pseg.meta("id","tech")
                n = n+(ttab+tab+"<span xml:id=\""+cid+"\" target=\"#"+pid+
                       "\" from=\"#"+s+"\" to=\"#"+e+"\"")
                if cseg.content:
                    n = n+(">"+html.escape(cseg.content)+"</span>\n")
                else:
                    n = n+("/>\n")
            n = n+(ttab+"\t</spanGrp>\n")
        txt = txt+n+(ttab+"</annotationBlock>\n"); n = ""
    f.write(txt+(tab+"\t</div>\n"+tab+"</body>\n\t</text>\n</TEI>"))   
def saveTEI(path,trans,encoding,ext):
    """Exports a single Transcription into a TEI file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - encoding      : (str) The TEI file encoding.
    - ext           : (str) The TEI file extension.
    RETURNS:
    - Creates a TEI file at 'path' from 'trans'.
    Note: 'path' is tested here, everything else should be known.
    """
    
        # Path
    if os.path.isdir(path):                     # If it's a directory
        path = os.path.join(path,trans.name+ext)# Use 'trans.name'
    encoding = _chEncoding(trans,encoding)      # Encoding
    ntrans = trans.copy()                       # We use a copy from there
    
    f = open(path,'w',encoding=encoding)        # Open file
    _writeHeader(f,ntrans,encoding)             # Write header
    d_timetable,id = _writeTimeTable(f,ntrans)  # Write timetable
    _writeBody(f,ntrans,d_timetable,id)         # Write tiers
    f.close()                                   # Close file
def _saveList(path,trans,encoding,ext):
    """Exports a list of / a Corpus' transcriptions into TEI files."""
    for tr in trans:
        saveTEI(path,tr,encoding,ext)

    # Main function
def toTEI(path,trans,**args):
    """Exports one or more TEIs.
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - encoding      : (str) The file encoding.
    - ext           : (str) The file extension (default '.xml').
    RETURNS:
    - Creates the TEI(s) at 'path' from 'trans'.
    Note: Creates a copy for each Transcription while exporting."""
    
        # Args
    encoding = args.get('encoding')     # file encoding (for all files)
    ext = args.get('ext','.xml')
        # Overload
    f = d_load.get(type(trans))
    if f:
        f(path,trans,encoding,ext)
    else:
        raise KeyError("First argument must be of type 'Transcription/"+
                       "/Corpus/list'.")
d_load = {Transcription:saveTEI,Corpus:_saveList,
          list:_saveList}