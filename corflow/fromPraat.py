"""25/11/2021

A TextGrid file (for Praat, Boersma & Weenink 1992-) has:
    - two types of tiers ('IntervalTier'/'TextTier')
    - three types of files ('text','short','binary')
And the file encoding. 
Note: Functions starting with '_' are not meant to be called by the user.

'fromPraat()' should be called. It in turn calls:
    > '_checkFiles()' to determine if 'path' is a dir/file, and call:
        > 'testEncoding()' to determine the type/encoding
It then calls, one or more times:
    > 'loadTGD()' to load the TextGrid file according to its type

Note: '_checkFiles()' only selects files with '.textgrid' (caps ignored)
      extensions.
Note: The encoding is automatically detected using the first 3 bytes of a file,
      with 'd_enc' structured as {3-bytes: encoding}.
      A UnicodeDecodeError likely means the file's encoding isn't in that
      dictionary.
Note: 'utf-8' will require reading the whole file once.
Note: Point tiers (TextTier type) are loaded with start/end time codes equal.
      Nothing else reveals their type.
Note: Each TextGrid type has its own function ('_loadX()') with sub-functions.
      They repeat themselves a lot but are kept almost entirely separate.
      While probably inefficient, this is intentional.
"""
from .Transcription import Transcription
import os,re,struct

    # Technical functions
def _escape(data):
    """Support function to clean the content"""
    
    data = data.replace("\"\"","\"")
    return data
def _chType(tier_type):
    """Turns tier_type into a boolean."""

    if tier_type == "IntervalTier":
        tier_type = True
    elif tier_type == "TextTier":
        tier_type = False
    return tier_type
def _textHeader(f):
    """Skipping the header for 'long/short' types."""
    line = "header_check"
    while not line == "\n":
        line = f.readline()
def testEncoding(path,type,encoding,
                 d_enc = {b'\x6f\x6f\x42':"binary",
                          b'\x46\x69\x6c':"utf_8",
                          b'\xef\xbb\xbf':"utf_8_sig",
                          b'\xfe\xff\x00':"utf_16_be",
                          b'\xff\xfe\x00':"utf_16_le"}):
    """Returns the assumed encoding/type if none has been given.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - type          : (str) A user-defined TextGrid type.
    - encoding      : (str) A user-defined file encoding.
    - d_enc         : (dict) A user-defined codec check dictionary
                            (default 'utf_8','utf_8(_sig)','utf_16(_be/le)').
    RETURNS:
    - type          : (str) A TextGrid type ('text','short','binary').
    - encoding      : (str) A file encoding.
    Note: If encoding is given, it's always applied blindy to all files.
          If type is given, it will be overwritten if encoding is missing.
    Note: Only handles 'd_enc' encodings. 'latin_1' derived from 'utf_8'."""
    
    def ch_error(f,encoding):
        if encoding == "utf_8":
            encoding = "latin_1"; f.close()
            f = open(path,'r',encoding=encoding)
            return f,encoding
        else:
            raise
    def _read(fpath,lt=-1):
        a = 0; lb = b''
        with open(fpath,'rb') as f:
            if lt < 0:
                lb = os.path.getsize(fpath)
            while a < lt:
                byte = f.read(1)
                if byte == "":
                    break
                lb = lb+byte; a += 1
        return lb
    def _read2(f,i_range):
        for a in range(i_range):
            f.readline()
        return f.readline()
        # Use user-defined (for all)
    if type and encoding:
        return type,encoding
    typ,enc = type,encoding
        # Otherwise we check the files
        # Encoding
    if not enc:
            ## We read 3 bytes
        oct3 = _read(path,3)
        if oct3 in d_enc:
            encoding = d_enc[oct3]
                # Binary
            if encoding == "binary":
                return "binary",encoding
            # Can't find the encoding
        else:
            return type,encoding
        # Type
    f = open(path,'r',encoding=encoding); ch_enc = True
    while ch_enc:                           # Skip 3 lines
        try:
            line = _read2(f,3)
            ch_enc = False
        except UnicodeDecodeError:
            f,encoding = ch_error(f,encoding)
    if line.startswith("xmin"):         # get the file type
        type = "text"
    else:
        type = "short"
    if not encoding == "utf_8":         # last part is for utf-8
        f.close(); return type,encoding
    ch_enc = True
    while ch_enc:
        try:                                # read rest of the file
            for line in f:
                continue
            ch_enc = False
        except UnicodeDecodeError:
            f,encoding = ch_error(f,encoding)
    f.close()
    return type,encoding
def _checkFiles(path,type,encoding,ch_ext=".textgrid",sym=[]):
    """Returns a list of '.TextGrid' files with their type and encoding."""
    
    def _checkFile(fpath,file,l_files):
        fi,ext = os.path.splitext(file); 
        if not ext.lower() == ch_ext:
            return
        t,enc = testEncoding(fpath,type,encoding)
        l_files.append((fpath,t,enc,fi,sym))
    
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
    # Loading functions
def _loadLong(path,trans,enc):
    """Loads a 'text file' TextGrid."""
    
    def _longText(f):
        """Recovers text from a line."""
        text = f.readline().split("\"",1)[1].replace("\n","").strip()
        while not re.search('(""|(?<!"))"$',text):
            text = text+"\n"+f.readline().replace("\n","").strip()
        return _escape(text[:-1])
    def _longNum(f,fl=False):
        """Recovers a number from a line."""
        if fl:
            num = float(f.readline().split('=',1)[1])
        else:
            num = int(f.readline().split('=',1)[1])
        return num
    def _longTime(f,ch=True):
        """Recovers xmin/xmax from a line each."""
        start = _longNum(f,True)
        if ch:
            end = _longNum(f,True)
        else:
            end = start
        return start,end
    def _longSeg(f,tier,ch,incr):
        """Loads a segment."""

            # Interval line
        f.readline()
            # (Creating the Segment instance)
        seg = tier.create(-1,"a{:d}".format(incr))
            # Segment xmin/xmax
        seg.start,seg.end = _longTime(f,ch)
            # Segment text
        seg.content = _longText(f)
        return incr+1
    def _longTier(f,incr):
        """Loads a tier."""
        
            # Item line
        f.readline()
            # Tier type
        tier_type = _chType(_longText(f))
            # Tier name (creating the Tier instance)
        tier = trans.create(-1,_longText(f))
            # Tier xmin/xmax
        tier.start,tier.end = _longTime(f)
            # Tier intervals (segments)
        i_int = _longNum(f)
        for b in range(i_int):
            incr = _longSeg(f,tier,tier_type,incr)
        return incr

    with open(path,'r',encoding=enc) as f:
            # header
        _textHeader(f)
            # Transcription xmin/xmax
        trans.start,trans.end = _longTime(f)
            # end of header
        f.readline()
            # number of tiers
        i_tiers = _longNum(f); incr = 0
        f.readline()
        for a in range(i_tiers):
            incr = _longTier(f,incr)
    return trans
def _loadShort(path,trans,enc):
    """Loads a 'short file' TextGrid."""
    
    def _shortText(f):
        """Recovers text from a line."""
        text = f.readline()[1:].replace("\n","").strip()
        while not re.search('(""|(?<!"))"$',text):
            text = text+"\n"+f.readline().replace("\n","").strip()
        return _escape(text[:-1])
    def _shortTime(f,ch=True):
        """Recovers xmin/xmax from a line each."""
        start = float(f.readline())
        if ch:
            end = float(f.readline())
        else:
            end = start
        return start,end
    def _shortSeg(f,tier,ch,incr):
        """Loads a segment."""
            # (Creating the Segment instance)
        seg = tier.create(-1,"a{:d}".format(incr))
            # Segment xmin/xmax
        seg.start,seg.end = _shortTime(f,ch)
            # Segment text
        seg.content = _shortText(f)
        return incr+1
    def _shortTier(f,incr):
        """Loads a tier."""

            # Tier type
        tier_type = _chType(_shortText(f))
            # Tier name (creating the Tier instance)
        tier = trans.create(-1,_shortText(f))
            # Tier xmin/xmax
        tier.start,tier.end = _shortTime(f)
            # Tier intervals (segments)
        i_int = int(f.readline())
        for b in range(i_int):
            incr = _shortSeg(f,tier,tier_type,incr)
        return incr

    with open(path,'r',encoding=enc) as f:
            # header
        _textHeader(f)
            # Transcription xmin/xmax
        trans.start,trans.end = _shortTime(f)
            # end of header (<exists>)
        f.readline()
            # number of tiers
        i_tiers = int(f.readline()); incr = 0
        for a in range(i_tiers):
            incr = _shortTier(f,incr)
    return trans
def _loadBinary(path,trans,enc):
    """Loads a 'binary file' TextGrid.
    Relies on 'struct'."""
    
    def _binHeader(f):
        """Skipping the header."""
        
        while True:
            byte = f.read(1)
            if byte == b'\x64': # 'd' of 'TextGrid'
                break
    def _binTime(f,ch=True):
        """Recovers xmin/xmax from 8 bytes each."""
        
        start = struct.unpack('>d',f.read(8))[0]
        if ch:
            end = struct.unpack('>d',f.read(8))[0]
        else:
            end = start
        return start,end
    def _binText(f):
        """Recovers text from unknown length."""
        
            # 2-bytes (big-endian) text length
            ## Can also be an 'FF' indicator
        bb = f.read(2); text = ""
        if bb == b'\xff\xff':   # BOM indicating 2-bytes per character
            i_text = struct.unpack('>h',f.read(2))[0]
            for b in range(i_text):
                text = text+f.read(2).decode("utf_16_be")
        else:                   # Otherwise 1-byte per character
            i_text = struct.unpack('>h',bb)[0]
            for b in range(i_text):
                text = text+f.read(1).decode("utf_8")
            # We reduce double-quotes to one
        return _escape(text)
    def _binSeg(f,tier,ch,incr):
        """Loads a segment."""
        
            # (Creating the Segment instance)
        seg = tier.create(-1,"a{:d}".format(incr))
            # Segment xmin/xmax
        seg.start,seg.end = _binTime(f,ch)
            # Segment text
        seg.content = _binText(f)
        return incr+1
    def _binTier(f,incr):
        """Loads a tier."""
    
            # Tier type
            ## Reduced to boolean (Interval/PointTier, else should be error)
        i_type = struct.unpack('B',f.read(1))[0]
        tier_type = _chType(f.read(i_type).decode("utf_8"))
            # Tier name (creating the Tier instance)
        tier = trans.create(-1,_binText(f))
            # Tier xmin/xmax
        tier.start,tier.end = _binTime(f)
            # Tier intervals (segments)
        i_int = struct.unpack('>I',f.read(4))[0]
            # Segments
        for b in range(i_int):
            incr = _binSeg(f,tier,tier_type,incr)
        return incr
    
    with open(path,'rb') as f:
            # header
        _binHeader(f)
            # Transcription xmin/xmax
        trans.start,trans.end = _binTime(f)
            # tiers? <exists>
        f.read(4)
            # Tiers
        i_tiers = struct.unpack('B',f.read(1))[0]; incr = 0
        for a in range(i_tiers):
            incr = _binTier(f,incr)
    return trans
def loadTGD(path,typ="text",enc="utf-8",name="",sym=[]):
    """Main function to load a given TextGrid.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - type          : (str) The TextGrid type.
    - enc           : (str) The encoding.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes TextGrid type and encoding (and 'name') are known.
    Note: 'TextTier' type has both time codes equal."""

        # New Transcription instance
    trans = Transcription(name=name)
        # Selection among the three TextGrid types
    if typ == "text":
        trans = _loadLong(path,trans,enc)
    elif typ == "short":
        trans = _loadShort(path,trans,enc)
    elif typ == "binary":
        trans = _loadBinary(path,trans,enc)
        # Segment cleaning (removing pauses or such)
    if sym:
        trans.remGaps(sym)
    return trans
    # Main function
def fromPraat(path, **args):
    """Imports one or more TextGrid(s).
    ARGUMENTS:
    - path          : (str) A full path to either a file or a directory.
    - type          : (str) The TextGrid type ('text','short','binary').
    - encoding      : (str) The encoding ('latin_1','utf_8',etc.).
    - ch_ext        : (str) The lower-case extension used to find files.
    - sym           : (lst<str>) List of symbols to remove some segments.
    RETURNS:
    - trans/l_trans : (pntr/list) Either a Transcription or a list of
                                  Transcriptions.
    Note: if provided, 'type' and 'encoding' will blindly apply to all files.
    Note: see 'testEncoding()' for the encodings automatically retrievable."""
    
        # Args
    type = args.get('type')                 # 'text','short','binary'
    encoding = args.get('encoding')         # file encoding (for all files)
    ch_ext = args.get('ext',".textgrid")    # The TextGrid extension...
    sym = args.get('sym',[])                # symbol(s) to remove segments
        # Get files
    l_files,ch_dir = _checkFiles(path,type,encoding,ch_ext,sym)
    if ch_dir == 1:                 # list of files
        l_trans = []
        for tup in l_files:
            l_trans.append(loadTGD(*tup))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadTGD(*l_files[0])


"""Assumptions on the TextGrid's 'binary' structure for '_loadBinary()'.

Header:
1. Fixed header 'ooBinaryFile'+'\x08'+'TextGrid' (21 bytes)
                (with '\x08' being the length of 'TextGrid')
2. Transcription xmin (8 bytes) and xmax (8 bytes)
3. '01 00 00 00' (4 bytes)
   (likely 'tiers? <exists>')
4. Number of tiers (1 byte)
Then for each tier:
1. Length of tier type (1 byte)
2. tier type ((1) bytes)
3. (optional) 'ff ff' 2-bytes text encoding (utf_16_be)
4. Length of tier name (2 bytes, big-endian)
5. tier name ((4) bytes)
6. Tier xmin (8 bytes) and xmax (8 bytes)
7. Number of intervals (4 octets, big-endian)
Then for each seg:
1. Interval xmin (8 bytes) and xmax (8 bytes)
2. (optional) 'ff ff' 2-bytes text encoding (utf_16_be)
3. Length of interval text (2 bytes, big-endian)
4. Interval text ((3) bytes, utf_8 or utf_16_be)

Note: Header 1 and 3 are skipped.
Note: Relies on Python's 'struct' module for floats and integers."""