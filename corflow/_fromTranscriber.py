
def _getTrans(trans,elem):
    """Add some metadata from 'Trans' element."""
    pass
def _getSpeakers(trans,elem):
    """Add speakers and their metadata."""
    pass
def _getTurn(trans,elem):
    pass
def loadTRS(path,name=""):
    """Main function to load a given TRS file.
    ARGUMENTS:
    - path          : (str) A full path to the file.
    - name          : (str) The Transcription name.
    RETURNS:
    - trans         : (pntr) A Transcription instance.
    Note: assumes encoding (and 'name') is known."""
    
        # New Transcription instance
    trans = Transcription(name=name,metadata={})
    root = None
    d_tag = {'Trans':_getTrans,
             'Speakers':_getSpeakers,
             'Turn':_getTurn}
    
    b_root = False
    for event, elem in ETree.iterparse(path, events=("start","end")):
            # Find root for operation (cleaning)
        if not b_root:
            root = elem
            b_root = True
        elif event == "end":
            f = d_tag.get(elem.tag)
            if f: # operate on given element
                f(trans,elem)
                par = root.find(f".//{elem.tag}/..")
                if par: # remove given element
                    par.remove(elem)
    root.clear()
    return trans
def fromTranscriber(path,**args):
    """Imports one or more TRS(s).
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
            l_trans.append(loadTRS(*tup))
        return l_trans
    elif ch_dir == 0 and l_files:   # single file
        return loadTRS(*l_files[0])