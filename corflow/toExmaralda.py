"""24.01.2023
Updated script from 'toExmaralda', Corflow v2.
No idea what version of Exmaralda this was based on.
Not tested yet but should work.

Metadata is still highly problematic, as user-defined metadata is mixed
with the rest; more importantly, 'unescape' calls are spread all around
and everything is filled statically, making for a heavy, cumbersome code.
Note: 'exb' subdivision should be used for tier/segment.
      That is especially relevant for the 'type' key.
"""
from .Transcription import Corpus,Transcription
import os,html

def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
        # No user-defined encoding
    if not encoding:
            # Check metadata for one
        return trans.meta('encoding','tech',empty="utf_8")
    else:
        return encoding
def _sepUD(d_d,l_e,div="exb"):
    """Separates metadata into 'd_meta' and 'd_other'.
    'd_other' is user-defined metadata. Escapes the content."""
    d_m,d_o,gen = {},{},None
    gen = d_d.items() if isinstance(d_d,dict) else d_d.iterMeta(div)
    for k,v in gen:
        if k in l_e:
            d_m[k] = html.escape(v)
        else:
            d_o[k] = html.escape(v)
    return d_m,d_o

def _writeMeta(f,trans,enc):
    """Writes the metadata part of the header."""
    
        # Retrieve metadata
    l_e = ['transcription-name','project-name','comment',
           'referenced-file','transcription-convention']
    d_m,d_o = _sepUD(trans,l_e) # Separate user-defined data
        # static
    enc = enc.replace("_","-")
    txt = ("<?xml version=\"1.0\" encoding=\"{}\"?>\n".format(enc)+
           "<!-- (c) http://www.rrz.uni-hamburg.de/exmaralda -->\n")
        # corpus/transcription names
    c_name = d_m.get('project-name',"")
    t_name = d_m.get('transcription-name',"")
    if not t_name:
        t_name = html.escape(trans.meta("name"))
    txt = txt+("<basic-transcription>\n\t<head>\n\t\t<meta-information>"
               "\n\t\t\t<project-name>{}</project-name>"
               "\n\t\t\t<transcription-name>{}</transcription-name>"
               .format(c_name,t_name))
        # audio files
    l_urls = trans.meta("referenced-file","exb",ch_list=True,empty=[])
    if not l_urls:
        l_urls = trans.meta("audio",ch_list=True,empty=[])
    for url in l_urls:
        url = html.escape(url)
        txt = txt+("\n\t\t\t<referenced-file url=\"{}\"/>".format(url))
        # user-defined metadata
    txt = txt+("\n\t\t\t<ud-meta-information>")
    for k,v in d_o.items():
        txt = txt+("\n\t\t\t\t<ud-information attribute-name=\"{}\">{}"
                   "</ud-information>".format(k,v))
    if d_o:
        txt = txt+("\n\t\t\t")
    comment = d_m.get("comment","")
    convention = d_m.get("transcription-convention","")
    txt = txt+("</ud-meta-information>"
               "\n\t\t\t<comment>{}</comment>"
               "\n\t\t\t<transcription-convention>{}"
               "</transcription-convention>"
               "\n\t\t</meta-information>"
               .format(comment,convention))
    f.write(txt)
def _writeSpeakers(f,trans):
    """Writes the speaker part of the header."""
    
    def _writeLang(txt,d_vals,key):
        l_lang = d_vals.get(key,[])
        txt = txt+"\n\t\t\t\t<{}>".format(key)
        for lang in l_lang:
            lang = html.escape(lang)
            txt = txt+("\n\t\t\t\t\t<language lang=\"{}\"/>".format(lang))
        if l_lang:
            txt = txt+"\n\t\t\t\t"
        txt = txt+"</{}>".format(key)
    
    txt = "\n\t\t<speakertable>"
    l_e = ['id','abbreviation','sex','languages-used',
           'l1','l2','comment']
    l_spk = trans.getSpk()
    for spk,d_vals in l_spk.items():
        d_m,d_o = _sepUD(d_vals,l_e) # Separate user-defined metadata
            # before language
        id,abr = d_m.get('id'),d_m.get('abbreviation',[""])
        sex = d_m.get('sex',[""])
        id = [html.escape(spk)] if not id else id
        txt = txt+("\n\t\t\t<speaker id=\"{}\">"
                   "\n\t\t\t\t<abbreviation>{}</abbreviation>"
                   "\n\t\t\t\t<sex value=\"{}\"/>"
                   .format(id[0],abr[0],sex[0]))
            # languages
        _writeLang(txt,d_vals,'languages-used')
        _writeLang(txt,d_vals,'l1')
        _writeLang(txt,d_vals,'l2')
            # user-defined metadata
        txt = txt+"\n\t\t\t\t<ud-speaker-information>"
        for k,v in d_o.items():
            txt=txt+("\n\t\t\t\t\t<ud-information attribute-name=\"{}\">{}"
                     "</ud-information>".format(k,v))
        if d_o:
            txt=txt+"\n\t\t\t\t"
        comment = d_m.get('comment',"")
        txt = txt+("</ud-speaker-information>"
                   "\n\t\t\t\t<comment>{}</comment>"
                   "\n\t\t\t</speaker>".format(comment))
    if l_spk:
        txt = txt+"\n\t\t"
    f.write(txt+"</speakertable>\n\t</head>")
def _writeTimeTable(f,trans):
    """Writes the timetable."""
    
    txt = "\n\t<basic-body>\n\t\t<common-timeline>"
    d_timetable = {}
    for a,ts in enumerate(trans.timetable()):
        id = "T"+str(a)
        txt = txt+("\n\t\t\t<tli id=\"{}\" time=\"{:.3f}\"/>"
                   .format(id,ts))
        d_timetable[ts] = id
    f.write(txt+"\n\t\t</common-timeline>")
    return d_timetable
def _writeTier(f,trans,a,tier,d_timetable):
    """Writes a tier."""
    
    l_e = ['speaker','category','type']
    txt = "\n\t\t<tier id=\"{}\"".format("TIE"+str(a))
        # tier variables
    spk = tier.meta("speaker")
    cat,typ = tier.meta("category"),tier.meta("type")
    d_m,d_o = _sepUD(tier,l_e,"omni")
    if not typ: # no preset 'typ' in metadata, must derive default structure
        typ = 't' if a == 0 else 'a'
        # Write metadata 
    if spk:
        txt = txt+" speaker=\"{}\"".format(spk)
    txt = txt+(" category=\"{}\" type=\"{}\" display-name=\"{}\">"
               .format(html.escape(cat),typ,html.escape(tier.name)))
    if d_o: # user-defined metadata
        txt = txt+"\n\t\t\t<ud-tier-information>"
        for k,v in d_o.items():
            txt=txt+("\n\t\t\t\t<ud-information attribute-name=\"{}\">{}"
                     "</ud-information>".format(k,v))
        txt = txt+"\n\t\t\t</ud-tier-information>"
        # Segments
    for seg in tier:
        s,e = d_timetable[seg.start],d_timetable[seg.end]
        txt = txt+"\n\t\t\t<event start=\"{}\" end=\"{}\">".format(s,e)
        for k,v in seg.iterMeta():
            v = html.unescape(v)
            txt = txt+("<ud-information attribute-name=\"{}\">{}"
                       "</ud-information>".format(k,v))
        txt = txt + "{}</event>".format(html.unescape(seg.content))
    f.write(txt+"\n\t\t</tier>")
def saveEXB(path,trans,encoding):
    """Exports a single Transcription into an EXB file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - encoding      : (str) The Exmaralda file encoding.
    RETURNS:
    - Creates an EXB file at 'path' from 'trans'.
    Note: 'path' is tested here, everything else should be known.
    """
    
        # Path
    if os.path.isdir(path):                     # If it's a directory
        path = os.path.join(path,trans.name+".exb") # Use 'trans.name'
    encoding = _chEncoding(trans,encoding)      # Encoding
    ntrans = trans.copy()                       # We use a copy from there

    f = open(path,'w',encoding=encoding)        # Open file
    _writeMeta(f,ntrans,encoding)               # Write metadata part
    _writeSpeakers(f,ntrans)                    # Write speaker part
    d_timetable = _writeTimeTable(f,ntrans)     # Write timetable
    
    for a,tier in enumerate(ntrans):
        _writeTier(f,trans,a,tier,d_timetable)  # Write tier level
    f.write("\n\t</basic-body>\n</basic-transcription>") # Write footer
    f.close()                                   # Close file
def _saveList(path,trans,encoding):
    """Exports a list of / a Corpus' transcriptions into EXB files."""
    for tr in trans:
        saveEXB(path,tr,encoding)

    # Main function
def toExmaralda(path,trans,**args):
    """Exports one or more EXBs.
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - encoding      : (str) The file encoding.
    RETURNS:
    - Creates the EXB(s) at 'path' from 'trans'.
    Note: Creates a copy for each Transcription while exporting."""
    
        # Args
    encoding = args.get('encoding')     # file encoding (for all files)
        # Overload
    f = d_load.get(type(trans))
    if f:
        f(path,trans,encoding)
    else:
        raise KeyError("First argument must be of type 'Transcription/"+
                       "/Corpus/list'.")
d_load = {Transcription:saveEXB,Corpus:_saveList,
          list:_saveList}