""" 05/02/2022
An Elan file (for Elan, <archive.mpi.nl/tla/elan>) has:
    - two types of tiers ('REF_ANNOTATION','ALIGNABLE_ANNOTATION')
Note: Follows the Annotation Format v3.0.
Note: Functions starting with '_' are not meant to be called by the user.

'fromElan()' should be called. It in turn calls:
    > '_checkFiles()' to determine if 'path' is a dir/file
It then calls, one or more times:
    > 'loadEAF()' to load the Elan file

Note: '_checkFiles()' only selects files with '.textgrid' (caps ignored)
      extensions.
Note: Generated tiers have both time codes and parents.
      LINGUISTIC_TYPE_REF is stored as 'type' in 'omni' metadata.
Note: All metadata at all levels is stored in 'elan' metadata.
      The Transcription level encompasses header, footer and document.
Note: Complex metadata (in header and footer) is stored with all attributes
      (and sub-elements) as a single block of text. See '_hyperval()' and
      '_readFooter()'.
"""
from .Transcription import Transcription
import xml.etree.cElementTree as ETree
import os,html

    # Dictionaries for segment/tier metadata
d_segMeta = {'EXT_REF':[],'SVG_REF':[],'CVE_REF':[],'LANG_REF':[]}
d_tierMeta = {'LINGUISTIC_TYPE_REF':[('omni','type')],
              'PARTICIPANT':[('omni','speaker')],
              'ANNOTATOR':[],
              'LANG_REF':[('omni','language')],
              'DEFAULT_LOCALE':[],
              'EXT_REF':[]}

def _checkFiles(path,ch_ext=".eaf"):
    """Returns a list of '.eaf' files."""
    
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
def _hyperval(el):
    """Recovers all attributes into a single string."""
    hyperval = ""
    for key,val in el.attrib.items():
        if hyperval:
            hyperval = hyperval+" "
        hyperval = hyperval+key+"=\""+html.escape(val)+"\""
    return hyperval

def _writeMD(d,obj,el):
    """Loads segment/tier metadata (using fixed dictionaries)."""
    for key,l_other in d.items():
        if key in el.keys():
            obj.setMeta(key,el[key],'elan',i=-1)
            for sub,k in l_other:
                obj.setMeta(k,el[key],sub,i=-1)
def _readTime(trans,elem,d_timeorder):
    """Support function to fill that timeorder.
    Adds transcription's start/end times."""
    
    l_ids = []
    for time in elem:
        l_ids.append(time.get("TIME_SLOT_ID"))
        if "TIME_VALUE" in time.attrib:
            d_timeorder[l_ids[-1]] = time.get("TIME_VALUE")
        else:
            d_timeorder[l_ids[-1]] = "-1000"
    start = d_timeorder[l_ids[0]]; end = d_timeorder[l_ids[-1]]
    trans.start = float(start[:-3] + '.' + start[-3:])
    trans.end = float(end[:-3] + '.' + end[-3:])
    return d_timeorder
def _readSegs(tier,elem,d_timeorder,d_segs,incr):
    """Loads the segments in the Tier instance."""
    
    def _readSegCont(el,c):
        """Recovers the segment's name and content."""
        
        if 'ANNOTATION_ID' in el.attrib.keys():
            name = html.unescape(el.attrib.get('ANNOTATION_ID'))
        else:
            name = "a"+str(incr); c += 1
        cont = ""
        for sub in el.iter():
            if sub.tag == 'ANNOTATION_VALUE':
                if sub.text:
                    cont = html.unescape(sub.text)
                break
        return name,cont,c
    def _readSegTime(el):
        start = -1.; end = -1.
        s_start = anno.attrib.get("TIME_SLOT_REF1")
        s_end = anno.attrib.get("TIME_SLOT_REF2")
        if s_start in d_timeorder:
            s_start = d_timeorder[s_start]
            start = float(s_start[:-3] + '.' + s_start[-3:])
        if s_end in d_timeorder:
            s_end = d_timeorder[s_end]
            end = float(s_end[:-3] + '.' + s_end[-3:])
        return start,end

        # We look for 'ALIGNABLE_ANNOTATION' (time alignment)
    for anno in elem.iter("ALIGNABLE_ANNOTATION"):
            # Segment content
        name,cont,incr = _readSegCont(anno,incr)
            # Segment start/end times
        start,end = _readSegTime(anno)
        seg = tier.create(-1,name,start,end,cont)
        d_segs[name] = [seg,True,""]
            # Segment metadata
        _writeMD(d_segMeta,seg,anno.attrib)

        # Otherwise we look for 'REF_ANNOTATION' (ref association)
    for anno in elem.iter("REF_ANNOTATION"):
            #Segment content
        name,cont,incr = _readSegCont(anno,incr)
            # Parenting
        ref = anno.attrib["ANNOTATION_REF"]
        seg = tier.create(-1,name,-1.,-1.,cont)
        d_segs[name] = [seg,False,ref]
            # Segment metadata
        _writeMD(d_segMeta,seg,anno.attrib)
    return d_segs,incr
def _readTier(trans,elem,d_timeorder,d_tiers,d_segs,incr):
    """Loads a tier into the Transcription instance."""
    
        # Create a new Tier
    tier = trans.create(-1,html.unescape(elem.attrib.get("TIER_ID","tier")),
                        trans.start,trans.end,elem=[],metadata={})
        # Tier metadata
    parent = elem.attrib.get('PARENT_REF')
    _writeMD(d_tierMeta,tier,elem.attrib)           # elan
    d_tiers[tier.name] = (tier,parent)
        # Segments
    incr = _readSegs(tier,elem,d_timeorder,d_segs,incr)
    return d_tiers,d_segs,incr
def _readHeader(trans,elem):
    """Reads the header. All PROPERTY tags added to 'omni'."""
    
    l_sub = ['MEDIA_DESCRIPTOR','LINKED_FILE_DESCRIPTOR']
    for key,val in elem.attrib.items(): # Header attributes
        if key == 'MEDIA_FILE':
            trans.setMeta('name',val,'omni',i=-1)
    for sub in elem.iter():
        if sub.tag in l_sub:            # Sub-fields (l_sub)
            trans.setMeta(sub.tag,_hyperval(sub),'elan',i=-1)
            if sub.tag == "MEDIA_DESCRIPTOR":   # 'audio' file metadata
                audio = sub.get("MEDIA_URL"); ch = sub.get("MIME_TYPE")
                if audio and ch and ch == "audio/x-wav":
                    trans.setMeta('audio',audio)
        else:                           # PROPERTY
            k = sub.attrib.get('NAME','PROPERTY')
            trans.setMeta(k,sub.text,'elan',i=-1)
def _readFooter(trans,root):
    """Reads footer and 'ANNOTATION_DOCUMENT' attributes.
    'name' and 'lang' can be added to 'omni'."""
    
    def _footerSingle(trans,el):        # reads attributes as block of text
        """Reads a single tag (LOCALE & EXTERNAL_REF)."""
        trans.setMeta(el.tag,_hyperval(el),'elan',i=-1)
    def _footerComplex(trans,el):       # reads sub-elements as block of text
        """Reads the CONTROLLED VOCABULARY part."""
        attr = _hyperval(el)+">\n"
        for cel in el.iter():   # CV_ENTRY
            if cel.tag == el.tag:
                continue
            attr = attr+ETree.tostring(cel).decode()
            val = _hyperval(cel)
            if val:
                attr = attr+" "
        attr = attr+"\t</"+el.tag+">\n"
        trans.setMeta(el.tag,attr,'elan',i=-1)
    def _footerLang(trans,el):          # adds 'lang' to 'omni' metadata
        trans.setMeta(el.tag,_hyperval(el),'elan',i=-1)
        lang = el.attrib.get("LANG_LABEL")
        if lang:
            trans.setMeta('lang',lang,'omni',i=-1)

        # ANNOTATION_DOCUMENT
    l_doc = ['AUTHOR','DATE','FORMAT','VERSION']
    for key,val in root.attrib.items():
        if key in l_doc:
            trans.setMeta(key,val,'elan',i=-1)   # elan
        if key == "MEDIA_FILE":
            trans.setMeta('name',val,i=-1)       # omni
        # Footer
    d_footer = {'LICENSE':_footerSingle,
                'LINGUISTIC_TYPE':_footerSingle,
                'CONTROLLED_VOCABULARY':_footerComplex,
                'LOCALE':_footerSingle,
                'EXTERNAL_REF':_footerSingle,
                'LEXICON_REF':_footerSingle,
                'LANGUAGE':_footerLang,
                'REF_LINK_SET':_footerComplex}
    for el in root:
        if el.tag not in d_footer:  # Ignore everything else
            continue
        d_footer[el.tag](trans,el)
    
def _fixStructure(trans,d_tiers,d_segs):
    """We complete the missing information."""

    def _timeSplit(l_el):
        """Gives each child a proportion of parent time."""
        lc = len(l_el)
        if lc == 0:
            return
        start = l_el[0].start; end = l_el[-1].end
        if lc > 0:          # Don't divide by zero
            dur = ((end-start)/lc)
        for a in range(lc):
            l_el[a].start = l_el[a]._decimal(start+(dur*a))
            l_el[a].end = l_el[a]._decimal(start+(dur*(a+1)))
    
        # Time_subdivision (replacing empty TIME_VALUEs)
    for tier in trans:
        if not tier.elem or tier.elem[0].start < 0.:
            continue
        l_segs = []; lt = len(tier); pos = 0
        for a,seg in enumerate(tier):
            if seg.start >= 0:
                if l_segs:
                    _timeSplit(l_segs)
                l_segs = [seg]
            else:
                l_segs.append(seg)
        if l_segs:
            _timeSplit(l_segs)

        # Tier parenting
    for name,l_val in d_tiers.items():
        tier,pname = l_val[0],l_val[1]
        ptier,_ = d_tiers.get(pname,(None,""))
        if ptier:
            tier.setParent(ptier)
        # Segment parenting
    for name,l_val in d_segs.items():
        seg,ch_time,ref = l_val[0],l_val[1],l_val[2]
        tier = seg.struct; ptier = tier.parent(); pseg = None
        if ch_time and ptier:
            pseg = trans.getTime(seg.start,ptier)
        elif ref:
            pseg = d_segs[ref][0]
        if pseg:
            seg.setParent(pseg)

        # And now the time codes
    trans.setChildTime()
    trans.setBounds()

def loadEAF(path,name=""):
    """Main function to load a given EAF file.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes encoding (and 'name') is known.
    Note: tier types are stored in metadata, segment 'ref' not kept."""
    
        # New Transcription instance
    trans = Transcription(name=name,metadata={})
    d_timeorder = {}; root = None; d_tiers = {}; d_segs = {}; incr = 0
    
    b_root = False
    for event, elem in ETree.iterparse(path, events=("start","end")):
            # Find root for operation (cleaning)
        if not b_root:
            root = elem
            b_root = True
        elif event == "end":
                # getTimeorder (/!\ not Timetable)
            if elem.tag == "TIME_ORDER":
                d_timeorder = _readTime(trans,elem,d_timeorder)
                root.remove(elem)
                # getTiers
            elif elem.tag == "TIER":
                d_tiers,d_segs,incr = _readTier(trans,elem,d_timeorder,
                                                d_tiers,d_segs,incr)
                root.remove(elem)
                # getHeader&Footer
            elif elem.tag == "HEADER":
                _readHeader(trans,elem)
                root.remove(elem)
            elif elem.tag == "ANNOTATION_DOCUMENT":
                _readFooter(trans,root)
                root.clear()
    _fixStructure(trans,d_tiers,d_segs)
    return trans
def fromElan(path,**args):
    """Imports one or more EAF(s).
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
            l_trans.append(loadEAF(*tup))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadEAF(*l_files[0])