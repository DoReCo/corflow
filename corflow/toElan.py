"""05/02/2021

An Elan file (for Elan, <archive.mpi.nl/tla/elan>) has:
    - two types of tiers ('REF_ANNOTATION','ALIGNABLE_ANNOTATION')
Note: Follows the Annotation Format v3.0.
Note: Functions starting with '_' are not meant to be called by the user.

'toElan()' should be called. It in turns calls:
    > 'saveEAF()' to save each Transcription into an Elan file

Note: 'toElan()' argument 'path' is overloaded (d_load) for a 'Transcription',
      'Corpus' or 'list'. For the latter two, '_saveList()' iterates.
Note: The tier 'LINGUISTIC_TYPE' is automatically set. Pre-existing types
      are adapted accordingly to ensure the file can be read by ELAN.
"""
from .Transcription import Corpus,Transcription
import os,html,math

    # Technical functions
def _chEncoding(trans,encoding):
    """Seeks encoding (default "utf_8")."""
    
        # No user-defined encoding
    if not encoding:
            # Check metadata for one
        return trans.meta('encoding','tech',empty="utf_8")
    else:
        return encoding
def _getMeta(trans):
    """Builds a dictionary of Elan types."""
    
    d_doc = {'DATE':[""],'AUTHOR':[""],'FORMAT':["3.0"],'VERSION':["3.0"],
             'MEDIA_FILE':[""],'TIME_UNITS':[""]} # default values
    d_header = {'MEDIA_DESCRIPTOR':[],'LINKED_FILE_DESCRIPTOR':[]}
    d_footer = {'LINGUISTIC_TYPE':[],'CONTROLLED_VOCABULARY':[],
                'LOCALE':[],'EXTERNAL_REF':[],'LEXICON_REF':[],
                'REF_LINK_SET':[],'LANGUAGE':[]}
    d_open = {}
    l_ops = [d_doc,d_header,d_footer]
    for key,l_val in trans.iterMeta('elan',ch_list=True):
        ch = False  # Fixed doc/header/footer fields
        for d in l_ops:
            if key in d:
                d[key] = l_val; ch = True; break
        if not ch:  # The rest is PROPERTY
            d_open[key] = l_val
    d_header['PROPERTY'] = d_open.copy()
    return d_doc,d_header,d_footer
def _readHyperval(txt):
    """Turns a string of attributes into a dict'."""
    d_attr = {}
    if not txt:
        return d_attr
    l_attr = [""]; ch1,ch2 = False,True
    for char in txt:
        if not ch2:
            ch2 = True
        elif not ch1:
            l_attr[-1] = l_attr[-1]+char
            if char == "\"":
                ch1 = True
        elif char == "\"":
            l_attr.append(""); ch1 = False; ch2 = False
        else:
            l_attr[-1] = l_attr[-1]+char
    if not l_attr[-1]:
        l_attr = l_attr[:-1]
    for attr in l_attr:
        key,val = attr.split("=\"")
        if val and val[-1] == "\"" and (not val[-2] == "\\"):
            val = val[:-1]
        d_attr[html.escape(key)] = html.escape(val)
    return d_attr
def _addTierAttr(text,l_attr):
    for key,val in l_attr:
        if val:
            text = text+" "+html.escape(key)+"=\""+html.escape(val)+"\""
    return text

    # Writing functions
def _writeHeader(f,trans,d_doc,d_header):
    """Writes the HEADER part of the file."""
    
        # ANNOTATION_DOCUMENT
    txt = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
           "<ANNOTATION_DOCUMENT DATE=\"{}\" AUTHOR=\"{}\" FORMAT=\"{}\" "
           "VERSION=\"{}\" xmlns:xsi=\"http://www.w3.org/2001/"
           "XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\""
           "http://www.mpi.nl/tools/elan/EAFv3.0.xsd\">\n\t<HEADER "
           .format(d_doc['DATE'][0],d_doc['AUTHOR'][0],
                   d_doc['FORMAT'][0],d_doc['VERSION'][0]))
        # LICENSE
    if trans.checkMeta('LICENSE',div='elan'):
        txt = txt+("<LICENSE {}/>\n"
                   .format(html.escape(trans.meta('LICENSE','elan'))))
        # HEADER attributes
    media_file,time_unit = d_doc['MEDIA_FILE'][0],d_doc['TIME_UNITS'][0]
    if not media_file and trans.checkMeta('name'):
        media_file = trans.meta('name')
    if media_file:
        txt = txt+"MEDIA_FILE=\"{}\" ".format(html.escape(media_file))
    if not time_unit:
        time_unit = "milliseconds"
    txt = txt+"TIME_UNITS=\"{}\">\n".format(time_unit)
        # HEADER sub-fields
    fixed = ""; open = ""; ch_audio = False
    for key,l_val in d_header.items():
        if key == "PROPERTY":                   # Open dictionary
            for k,l_v in l_val.items():
                for v in l_v:
                    open = open+("\t\t<PROPERTY NAME=\"{}\">{}</PROPERTY>\n"
                                 .format(k,v))
            continue
        elif key == "MEDIA_DESCRIPTOR":
            ch_audio = True
        for val in l_val:                       # Fixed dict
            fixed = fixed+("\t\t<{} {}/>\n".format(key,val))
    if not ch_audio and trans.checkMeta('audio'):   # omni 'audio'
        l_audio = trans.meta('audio',ch_list=True)
        for audio in l_audio:
            fixed = fixed+("\t\t<MEDIA_DESCRIPTOR MEDIA_URL=\"{}\">\n"
                           "MIME_TYPE=\"audio/x-wav\""
                           .format(html.escape(audio)))
        # Write to file
    f.write(txt+fixed+open+"\t</HEADER>")
def _writeTimeTable(f,trans):
    """Writes the TIME_ORDER part."""
    
    timetable = trans.timetable()
    d_timetable = {}; txt = "\n\t<TIME_ORDER>\n"
    for a,ts in enumerate(timetable):
        id = "ts"+str(a+1)
        t = ("{:.3f}".format(ts)).replace('.','')
        txt = txt+("\t\t<TIME_SLOT TIME_SLOT_ID=\""+id+"\" TIME_VALUE="
                   "\""+t+"\"/>\n")
        if not ts in d_timetable:
            d_timetable[ts] = id
    f.write(txt+"\t</TIME_ORDER>\n")
    return d_timetable
def _writeRefSeg(tier):
    """Return REF_ANNOTATION to '_writeTier()'."""
    id = ""; ref = ""; l_prev = []; o_ref = None; txt=""
        # We reconstitute the "prev"
    for a,seg in enumerate(tier):
        if not seg.parent() == o_ref:
            l_prev.append(""); o_ref = seg.parent()
        else:
            l_prev.append(tier.elem[a-1].name)
        # We write
    for a,seg in enumerate(tier):
        if not seg.parent():
            ptier = tier.parent().name if tier.parent() else "None"
            raise ValueError("A segment has no parent: {},{},{:.04f},{:04f},{}"
                             .format(tier.name,ptier,
                                     seg.start,seg.end,seg.content))
        txt = txt+("\t\t<ANNOTATION>\n\t\t\t<REF_ANNOTATION "
                   "ANNOTATION_ID=\"{}\" ANNOTATION_REF=\"{}\""
                   .format(html.escape(seg.name),
                           html.escape(seg.parent().name)))
        if not l_prev[a] == "":
            txt = txt+(" PREVIOUS_ANNOTATION=\"{}\""
                      .format(html.escape(l_prev[a])))
        for k,v in seg.iterMeta('elan'):
            txt = txt+" {}=\"{}\"".format(html.escape(k),html.escape(v))
        txt = txt+(">\n\t\t\t\t<ANNOTATION_VALUE>{}</ANNOTATION_VALUE>"
                   "\n\t\t\t</REF_ANNOTATION>\n\t\t</ANNOTATION>\n"
                   .format(html.escape(seg.content)))
    return txt
def _writeTimeSeg(tier,d_timetable):
    """Returns ALIGNABLE_ANNOTATION to '_writeTier()'."""
    ts1 = ""; ts2 = ""; txt = ""
    for seg in tier.elem:
        ts1 = d_timetable[seg.start]; ts2 = d_timetable[seg.end]
        txt = txt+("\t\t<ANNOTATION>\n\t\t\t<ALIGNABLE_ANNOTATION "
                   "ANNOTATION_ID=\"{}\" TIME_SLOT_REF1=\"{}\" "
                   "TIME_SLOT_REF2=\"{}\""
                   .format(html.escape(seg.name),ts1,ts2))
        for k,v in seg.iterMeta('elan'):
            txt = txt+" {}=\"{}\"".format(html.escape(k),html.escape(v))
        txt = txt+(">\n\t\t\t\t<ANNOTATION_"
                   "VALUE>{}</ANNOTATION_VALUE>\n\t\t\t"
                   "</ALIGNABLE_ANNOTATION>\n\t\t</ANNOTATION>\n"
                   .format(html.escape(seg.content)))
    return txt
def _setTypes(trans):
    """Sets the tier types."""
    
    def testType(tier,ptier):
        """We need to know the type."""

        tn = tier.name; pn = ptier.name if ptier else "None"
        typ = 'assoc'
        if not ptier:                   # Independent tier, time-aligned
            return 'time'
        ch_subd = False; ch_time = False
        for pseg in ptier:              # Iterate over all segments if need be
            d_child = pseg.childDict()
            if (not tier in d_child) or len(d_child[tier]) <= 1:# ASSOC
                continue
            typ = 'subd'                # SUBD
            l_child = d_child[tier]
            lc = len(l_child); dur = (pseg.end-pseg.start)/lc
            for a,cseg in enumerate(l_child):
                s = pseg.start+(a*dur); e = pseg.start+((a+1)*dur)
                if ((not math.isclose(cseg.start,s,abs_tol=0.001)) or
                    (not math.isclose(cseg.end,e,abs_tol=0.001))):
                    return 'subtime'    # INCLUDED-IN
        return typ
    
    l_child = []; d_typs = {}
        # Setup 'type' for LINGUISTIC_TYPE_ID/REF
    for tier in trans:                              # Test each tier
        typ = tier.meta('type','tech')
        if not typ:
            typ = testType(tier,tier.parent())
        typ_id = tier.meta('type')
        if not typ_id:
            tier.setMeta('type',typ,i=-1); typ_id = typ
        tier.setMeta('type',typ,'tech')
        if not typ_id in d_typs:                    # check omni-type
            d_typs[typ_id] = [tier]
        else:
            d_typs[typ_id].append(tier)
        if tier.parent() and not tier.children():   # bottom tiers
            l_child.append(tier)
        # Time_Subdivision/Included_In require parent also time-aligned
    for ctier in l_child:                           # check 'subtime'
        ctyp = ctier.meta('type','tech'); ch_time = False
        if ctyp == "subtime":
            ch_time = True
        tier = ctier.parent(); ptier = tier.parent()
        while ptier:                                # For each parent
            if ch_time:                             # set parent ('tier')
                tier.setMeta('type',"subtime",'tech')
            elif tier.meta('type','tech') == "subtime":# prep' for next
                ch_time = True
            tier = ptier; ptier = tier.parent()     # new parent
        # ?
    for typ_id,l_tpl in d_typs.items():             # Prevent TYPE overwrite
        o_typ = ""
        for tier in l_tpl:
            typ = tier.meta('type','tech')
            if not o_typ:                           # First round
                o_typ = typ
            elif not o_typ == typ:                  # Any divergence...
                tier.setMeta('type',typ)
def _writeTier(f,a,tier,d_timetable):
    """Writes a tier tag in the file."""
    
    def testMeta(txt,tier,l_attr):
        """We add 'elan' metadata, skipping what 'omni' provided."""
        for key,val in tier.iterMeta('elan'):
            ch = True
            for tpl in l_attr:
                if key == tpl[0]:
                    ch = False; break
            if ch:
                txt = txt+" "+html.escape(key)+"=\""+html.escape(val)+"\""
        return txt
    
        # Get type
    ptier = tier.parent(); typ = tier.meta('type','tech')
    typ_id = tier.meta('type')
    if not typ_id:
        tier.setMeta('type',typ,i=-1); typ_id = typ
    txt = ("\t<TIER TIER_ID=\""+html.escape(tier.name)+"\"")
        # Add tier metadata
    l_attr = [('PARENT_REF',None),
              ('LINGUISTIC_TYPE_REF',tier.meta('type')),
              ('PARTICIPANT',tier.meta('speaker')),
              ('LANG_REF',tier.meta('lang')),
              ('ANNOTATOR',tier.meta('author'))]
    if ptier:
        l_attr[0] = ('PARENT_REF',ptier.name)
    txt = _addTierAttr(txt,l_attr)              # 'omni' metadata
    txt = testMeta(txt,tier,l_attr)             # 'elan' metadata
    tier.setMeta('type',typ,'tech',i=0)
    if not tier.elem:                       # Check to end early
        f.write(txt+" />\n"); return
    txt = txt+">\n"
        # SEGMENTS
    if typ == "assoc" or typ == "subd":         # assoc/subd
        txt = txt+_writeRefSeg(tier)
    else:                                       # time/subtime
        txt= txt+_writeTimeSeg(tier,d_timetable)
    f.write(txt+"\t</TIER>\n")
def _writeFooter(f,trans,d_footer):
    """Writes the footer part of the file."""
    
    def checkTyp(d_attr,d_typ,l_conv):
        """We need to compare tiers and LINGUISTIC_TYPEs."""
            # Find if they are of the same type
        attr_id = d_attr.get('LINGUISTIC_TYPE_ID')          # LINGU ID
        if not attr_id in d_typ:
            return {}
        n_typ = d_typ[attr_id]; tier_typ = ""               # tier name_type
        for tpl in l_conv:                                  # tier type
            if n_typ == tpl[1]:
                tier_typ = tpl[0]; break
        cons = d_attr.get('CONSTRAINTS',""); attr_typ = ""  # LINGU type
        for tpl in l_conv:                                  # LINGU name_type
            if cons in tpl[0]:
                a_typ = tpl[1]; break
        if attr_typ == tier_typ:                            # Same type
            return d_attr
            # If they are not of the same type...
        if cons and n_typ == 'time':                        # CONSTRAINTS
                d_attr.pop('CONSTRAINTS')
        if not n_typ == 'time':
            d_attr['CONSTRAINTS'] = tier_typ
            if n_typ == 'subtime':                          # TIME_ALIGNABLE
                d_attr['TIME_ALIGNABLE'] = "true"
            else:
                d_attr['TIME_ALIGNABLE'] = "false"
        return d_attr
    def checkTier(d_typ,d_ntyp):
        """Add the tiers missing from the previous footer."""
        for tier_type,tier_truetype in d_typ.items():           # tiers
            if tier_type in d_ntyp:
                continue
            algn = "true"; cons = ""
            for a,tpl in enumerate(l_conv):
                if tier_truetype == tpl[1]:
                    cons = tpl[0]
                    if a > 1:
                        algn = "false"
                    break
            d_ntyp[tier_type] = {'LINGUISTIC_TYPE_ID':tier_type,
                                 'GRAPHIC_REFERENCES':"false",
                                 'TIME_ALIGNABLE':algn}
            if cons:
                d_ntyp[tier_type]['CONSTRAINTS'] = cons
    
    txt = ""
        # LINGUISTIC_TYPE
    d_typ = {}
    d_typ = {tier.meta('type'):tier.meta('type','tech') for tier in trans}
    l_conv = [('Included_In','subtime'),
              ('Time_Subdivision','subtime'),
              ('Symbolic_Subdivision','subd'),
              ('Symbolic_Association','assoc')]
    d_ntyp = {}
    for val in d_footer['LINGUISTIC_TYPE']:                 # previous footer
        d_attr = checkTyp(_readHyperval(val),d_typ,l_conv)
        if d_attr:
            d_ntyp[d_attr['LINGUISTIC_TYPE_ID']] = d_attr
    checkTier(d_typ,d_ntyp)                                 # remaining tiers
    for typ,d_attr in d_ntyp.items():
        txt = txt+"\t<LINGUISTIC_TYPE"
        for k,v in d_attr.items():
            txt = txt+" {}=\"{}\"".format(k,v)
        txt = txt+"/>\n"
    d_footer.pop('LINGUISTIC_TYPE')
        # LANGUAGE
    d_lang = {}
    for val in d_footer['LANGUAGE']:
        d_attr = _readHyperval(val); langu = d_attr.get('LANG_LABEL')
        if langu:
            d_lang[langu] = True
        txt = txt+"\t<LANGUAGE "+val+"/>\n"
    l_val = trans.meta('lang',ch_list=True)
    for val in l_val:
        if val in d_lang:
            continue
        txt = txt+("\t<LANGUAGE LANG_ID=\"{}\" LANG_LABEL=\"{}\"/>\n"
                   .format(html.escape(val),html.escape(val)))
        # EVERYTHING ELSE
    for key,l_val in d_footer.items():
        if key == 'LINGUISTIC_TYPE' or key == 'LANGUAGE':
            continue
        for val in l_val:
            txt = txt+"\t<"+key
            if val:
                txt = txt+" "+val
            if not val.endswith("\n"):
                txt = txt+"/>\n"
        # FIXED CONSTRAINTS
    txt = txt+("\t<CONSTRAINT STEREOTYPE=\"Time_Subdivision\" DESCRIPTION=\""
         "Time subdivision of parent annotation's time interval, no time "
         "gaps allowed within this interval\"/>\n\t<CONSTRAINT STEREOTYPE="
         "\"Symbolic_Subdivision\" DESCRIPTION=\"Symbolic subdivision of a "
         "parent annotation. Annotations refering to the same parent are "
         "ordered\"/>\n\t<CONSTRAINT STEREOTYPE=\"Symbolic_Association\" "
         "DESCRIPTION=\"1-1 association with a parent annotation\"/>\n\t"
         "<CONSTRAINT STEREOTYPE=\"Included_In\" DESCRIPTION=\"Time alignable "
         "annotations within the parent annotation's time interval, gaps are "
         "allowed\"/>\n")
         # End of ANNOTATION_DOCUMENT
    txt = txt+"</ANNOTATION_DOCUMENT>"
    f.write(txt)
def saveEAF(path,trans,encoding):
    """Exports a single Transcription into an EAF file.
    ARGUMENTS:
    - path          : (str) Full path to a directory or file.
    - trans         : (pntr) A Transcription instance.
    - encoding      : (str) The Elan file encoding.
    RETURNS:
    - Creates an EAF file at 'path' from 'trans'.
    Note: 'path' is tested here, everything else should be known.
    """
    
        # Path
    if os.path.isdir(path):                     # If it's a directory
        path = os.path.join(path,trans.name+".eaf")     # Use 'trans.name'
    encoding = _chEncoding(trans,encoding)      # Encoding
    ntrans = trans.copy()                       # We use a copy from there
    d_doc,d_header,d_footer = _getMeta(ntrans)  # We recover the metadata

    f = open(path,'w',encoding=encoding)        # Open file
    _writeHeader(f,ntrans,d_doc,d_header)       # Write transcription level
    _setTypes(ntrans)                           # Set tier types
    d_timetable = _writeTimeTable(f,ntrans)     # Write timetable
    
    for a,tier in enumerate(ntrans):
        _writeTier(f,a,tier,d_timetable)        # Write tier level
    _writeFooter(f,ntrans,d_footer)             # Write footer
    f.close()                                   # Close file
def _saveList(path,trans,encoding):
    """Exports a list of / a Corpus' transcriptions into EAF files."""
    for tr in trans:
        saveEAF(path,tr,encoding)

    # Main function
def toElan(path,trans,**args):
    """Exports one or more EAFs.
    ARGUMENTS:
    - path          : (str) A full path to either a directory or a file.
    - trans         : (overloaded) A Transcription, Corpus or list of
                                   Transcriptions.
    - encoding      : (str) The file encoding.
    RETURNS:
    - Creates the EAF(s) at 'path' from 'trans'.
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
d_load = {Transcription:saveEAF,Corpus:_saveList,
          list:_saveList}