"""25/11/2021

A TextGrid file (for Praat, Boersma & Weenink 1992-) has:
    - two types of tiers ('IntervalTier'/'TextTier')
    - three types of files ('text','short','binary')
And the file encoding. 
Note: Functions starting with '_' are not meant to be called by the user.

'toPraat()' should be called. It in turns calls:
    > 'saveTGD()' to save each Transcription into a TextGrid file

Note: 'toPraat()' argument 'path' is overloaded (d_load) for a 'Transcription',
      'Corpus' or 'list'. For the latter two, '_saveList()' iterates.
Note: 'TextTier' types (point tiers) are detected by checking the first 10
      segments (or less) of a tier. If any has differing start/end time codes,
      tier type is 'IntervalTier'.
Note: '_writeX()' uses ifs statements for each type of file/tier.
      While probably inefficient, this is intentional.
"""
from .Transcription import Corpus,Transcription
import os,struct

    # Technical functions
def _escape(data):
    """Support function to replace xml>sax>saxutils."""
    
    data = data.replace("&quot;","\"").replace("&apos;","'") \
               .replace("&lt;","<").replace("&gt;",">") \
               .replace("&amp;","&").replace("\"","\"\"")
    return data
def _writeBinText(s):
    """Turns a string into either 'utf_8' or 'utf_16_be' bytearray..."""
    s = _escape(s)
    lb = struct.pack('>h',len(s))
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        return b'\xff\xff'+lb+s.encode('utf_16_be')
    else:
        return lb+s.encode('utf_8')
def _writeBinFloats(start,end):
    return bytearray(struct.pack('>d', start))+bytearray(struct.pack('>d', end))
def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
        # No user-defined encoding
    if not encoding:
            # Check metadata for one
        encoding = trans.meta('encoding','tech')
        if encoding:
            return encoding         # In 'tech' metadata
        else:
            return "utf_8"          # Default
    else:
        return encoding
    # Writing functions
def _writeHeader(f,trans,typ):
    """Writes the file's header."""
    
    if typ == "text":
        f.write("File type = \"ooTextFile\"\nObject class ="
                " \"TextGrid\"\n\nxmin = {:.3f}\nxmax = {:.3f}"
                "\ntiers? <exists>\nsize = {}\nitem []:\n"
                .format(trans.start,trans.end,len(trans.elem)))
    elif typ == "short":
        f.write("File type = \"ooTextFile\"\nObject class ="
                " \"TextGrid\"\n\n{:.3f}\n{:.3f}\n<exists>\n{}\n"
                .format(trans.start,trans.end,len(trans.elem)))
    elif typ == "binary":
        lb = b'ooBinaryFile\x08TextGrid'                # fixed header
        lb = lb + _writeBinFloats(trans.start,trans.end)# xmin/xmax
        lb = lb + b'\x01\x00\x00\x00'                   # tiers exist
        lb = lb + struct.pack('B',len(trans.elem))     # nb of tiers
        f.write(lb)
def _writeTier(f,a,tier,t_type,typ):
    """Writes a tier header in the file."""
    
    if typ == "text":
            # Need more text
        if t_type == "IntervalTier":
            last = "intervals"
        elif t_type == "TextTier":
            last = "points"
        f.write("\titem [{}]:\n\t\tclass = \"{}\"\n\t\tname"
                " = \"{}\"\n\t\txmin = {:.3f}\n\t\txmax"
                " = {:.3f}\n\t\t{}: size = {}\n"
                .format(a+1,t_type,_escape(tier.name),tier.start,tier.end,
                        last,len(tier.elem)))
    elif typ == "short":
        f.write("\"{}\"\n\"{}\"\n{:.3f}\n{:.3f}\n{}\n"
                .format(t_type,_escape(tier.name),tier.start,tier.end,
                        len(tier.elem)))
    elif typ == "binary":
        lb = struct.pack('B',len(t_type))+t_type.encode('utf_8')# t_type
        lb = lb + _writeBinText(tier.name)                      # name
        lb = lb + _writeBinFloats(tier.start,tier.end)          # xmin/xmax
        lb = lb + struct.pack('>I',len(tier))                   # nb of segs
        f.write(lb)
def _writeSeg(f,a,seg,t_type,typ):
    """Writes a segment (interval) in the file."""
    
    if typ == "text":
        if t_type == "IntervalTier":
            f.write("\t\tintervals [{}]:\n\t\t\txmin = {:.3f}"
                    "\n\t\t\txmax = {:.3f}\n\t\t\ttext = \"{}\"\n"
                    .format(a+1,seg.start,seg.end,_escape(seg.content)))
        elif t_type == "TextTier":
            f.write("\t\tpoints [{}]:\n\t\t\tnumber = {:.3f}"
                    "\n\t\t\tmark = \"{}\"\n"
                    .format(a+1,seg.start,_escape(seg.content)))
    elif typ == "short":
        if t_type == "IntervalTier":
            f.write("{:.3f}\n{:.3f}\n\"{}\"\n"
                    .format(seg.start,seg.end,_escape(seg.content)))
        if t_type == "TextTier":
            f.write("{:.3f}\n\"{}\"\n".format(seg.start,_escape(seg.content)))
    elif typ == "binary":
        if t_type == "IntervalTier":
            lb = _writeBinFloats(seg.start,seg.end)
        elif t_type == "TextTier":
            lb = bytearray(struct.pack('f', seg.start))
        lb = lb + _writeBinText(seg.content)
        f.write(lb)
def saveTGD(path,trans,typ,encoding,check,sym):
    """Exports a single Transcription into a TextGrid file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - type          : (str) The TextGrid file type.
    - encoding      : (str) The TextGrid file encoding.
    - check         : (bool) Whether to check boundaries / for overlaps.
    - sym           : (str) A symbol for 'fillGaps()'.
    RETURNS:
    - Creates a TextGrid file at 'path' from 'trans'.
    Note: 'path' is tested here, everything else should be known.
    Note: 'TextTier' type is tested on the first 10 segments or less.
          If any has differing start/end time codes, type is 'IntervalTier'.
    """
    
        # Path
    if os.path.isdir(path):                             # If it's a directory
        path = os.path.join(path,trans.name+".TextGrid")# Use 'trans.name'
    encoding = _chEncoding(trans,encoding)      # Encoding
    trans = trans.copy()                        # We use a copy from there
    if check:                                   # Check bounds and overlaps
        trans.setBounds(); trans.fixOverlaps()
    if typ == "binary":                         # Open file
        f = open(path,'wb')
    else:
        f = open(path,'w',encoding=encoding)
    _writeHeader(f,trans,typ)                   # Write transcription level
    for a,tier in enumerate(trans):
        t_type = 'TextTier'
            # Check if 'TextTier' type (point tier)
        for b in range(len(tier)):
            if not tier.elem[b].start == tier.elem[b].end or b > 10:
                    # IntervalTier type > call 'fixGaps()'
                t_type = 'IntervalTier'; tier.fixGaps(sym)
                break
        _writeTier(f,a,tier,t_type,typ)        # Write tier level
        for b in range(len(tier)):              # Write segment level
            _writeSeg(f,b,tier.elem[b],t_type,typ)
    f.close()                                   # Close file
def _saveList(path,trans,typ,encoding,check,sym):
    """Exports a list of / a Corpus' transcriptions into TextGrid files."""
    for tr in trans:
        saveTGD(path,tr,typ,encoding,check,sym)
    # Main function
def toPraat(path,trans,**args):
    """Exports one or more TextGrids.
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - type          : (str) The TextGrid file type ('text','short','binary').
    - encoding      : (str) The file encoding.
    - check         : (bool) Checks min/max boundaries and for overlaps.
    - sym           : (str) A symbol for added segments.
    RETURNS:
    - Creates the TextGrid(s) at 'path' from 'trans'.
    Note: Creates a copy for each Transcription while exporting.
    Note: Will add segments in gaps
          (see 'Tier.fillGaps()' in 'Transcription.py')."""
    
        # Args
    typ = args.get('type',"text")      # 'text','short','binary'
    encoding = args.get('encoding')     # file encoding (for all files)
    check = args.get('check',False)     # checking the structure
    sym = args.get('sym',"_")           # symbol for missing segments
        # Overload
    f = d_load.get(type(trans))
    if f:
        f(path,trans,typ,encoding,check,sym)
    else:
        raise KeyError("First argument must be of type 'Transcription/"+
                       "/Corpus/list'.")
d_load = {Transcription:saveTGD,Corpus:_saveList,
          list:_saveList}