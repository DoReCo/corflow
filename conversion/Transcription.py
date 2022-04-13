"""05/02/2021
Imports and exports 

Note:   'str' (string), 'int' (integer), 'float', 'list', 'dict' (dictionary)
        and 'pntr' (pointer) are used to describe the variable's type.
Note:   for x the variable, 'y_x' has 'y' indicate the variable's type. Per
        convention 's_' (str), 'i_' (int), 'f_' (float), 'l_' (list), 't_'
        (tuple) and 'd_' (dict).
        Those can be recursive: 'dl_x' means a dictionary of lists.
Note:   A 'reference' is a tuple (str,int,object) describing the object by
        its name, index and the object itself, as pointer.

All classes "Corpus > Transcription > Tier > Segment" are children of
'Conteneur', with:
- name,start/end & content  the name and content between two time codes
- elem                      a list of sub-elements
- d_elem                    the structure of those sub-elements
- metadata                  all information beyond start/end/content
A Corpus has a list of Transcriptions, a Transcription a list of Tiers, etc.
Note:   'd_elem' has an element's name as key and a list as value.
        In that list the first position is the element's index in 'elem',
        the second position the element's parent (as pointer).
        All positions beyond that are children elements (as pointers).
Note:   'metadata' is a structure "dict<str:dict<str:list<str>>>", or:
        > X.metadata['elan']['LOCALE'] = ["value1","value2"]
        Where two 'LOCALE' metadata for an Elan file are stored.
        The first key is the file format, with two strings reserved:
        - 'omni' for metadata shared by all file formats and
        - 'tech' for information used internally by CorFlow
"""
 
import re

    #### Support class ####
    #######################
class Conteneur:
    """Parent class to be inherited by all main classes."""
    
    def __init__(self,name="",start=-1.,end=-1.,content="",elem=[],
                 struct=None,d_elem={},metadata={}):
        self.name = name            # (string) name
        self.start = start          # (float) start time boundary
        self.end = end              # (float) end time boundary
        self.content = content      # (string) text contained
        self.elem = elem            # (lst<pntr>) list of elements
            # structure variables
        self.struct = struct        # (pntr) its container
        self.d_elem = d_elem        # (dct<pntr:lst<pntr>>) its elements
            # metadata variables
        self.metadata = metadata.copy()# (dict<str:lst<str>>) open metadata

        # default functions
    def __bool__(self):
        return True
    def __len__(self):
        return len(self.elem)
    def __iter__(self):
        for el in self.elem:
            yield el
    def iter(self):
        """Same as '__iter__()' but for references (name,index,pointer)."""
        for a in range(0,len(self.elem)):
            yield (self.elem[a].name,a,self.elem[a])

        # Technical functions
        ## Not meant to be accessed by the user
    def _iterstruct(self,l_struct):
        """Technical function for structure iterators."""
        for tpl in l_struct:
            yield tpl
    def _retEmpty(self,det=False):
        """Technical function to return a not-found case."""
        if det:
            return ("",-1,None)
        else:
            return None
    def _retDet(self,elem,det=False):
        """Technical function to return a case."""
        if not elem:
            return self._retEmpty(det)
        if det:
            return (elem.name,elem.index(),elem)
        else:
            return elem
    def _parDict(self,l_par,det=False):
        d_parent = {}
        for obj in l_par:
            if isinstance(obj,tuple):
                name,index,obj = obj
            d_parent[obj.struct] = self._retDet(obj,det)
    def _childDict(self,l_children,det=False):
        """Technical function to build a dict' of children elements."""
        d_children = {} # (dict) <struct: [_retDet(child)]>
        for obj in l_children:
            if isinstance(obj,tuple):
                name,index,obj = obj
            if obj.struct in d_children:
                d_children[obj.struct].append(self._retDet(obj,det))
            else:
                d_children[obj.struct] = [self._retDet(obj,det)]
        return d_children
    def _mdList(self,l_res,ch_list,empty):
        """Returns a list or a string."""
        if ch_list:                         # must return a list
            if not l_res:                   # empty list
                return []
            for a,el in enumerate(l_res):   # replace by default empty
                if not el:
                    l_res[a] = empty
            return l_res                    # return list
        elif not l_res:                     # return default empty
            return empty
        else:                               # return first value
            return l_res[0]
        # technical get/set functions
    def _fixIndex(self,index):
        if index < 0 or index > len(self.elem):
            index = len(self.elem)
        return index
    def _fixIndexes(self,struct,start,end):
        """After moving, adding or removing, we need to fix indes."""
        if start < 0:
            start = 0
        if end > len(struct):
            end = len(struct)
        for a in range(start,end):
            el = struct.elem[a]
            struct.d_elem[el][0] = a
    def _fixName(self,name,struct=None):
        test = name; c = 0; ch = True
        while ch:
            ch = False
            for el in struct.elem:
                if el.name == test:
                    ch = True; test = name+str(c); c+=1; break
        return test
    def _fixStruct(self,struct):
        if not struct:
            struct = self
        return struct
    def _fixSelfStruct(self,struct):
        if not struct:
            struct = self.struct
        return struct
    def _decimal(self,num):
        return float("{:.4f}".format(num)[:-1])
    def _split(self,l_el,pel):
        """Gives each child a proportion of parent time.
        'pel' "overloaded" for 'tuple' or 'Conteneur'."""
        lc = len(l_el); s,e = -1.,-1.
        if type(pel) == tuple:  # 'overload'
            s,e = pel[0],pel[1]
        elif pel:
            s,e = pel.start,pel.end
        if lc > 0:          # Don't divide by zero
            dur = ((e-s)/lc)
        for a in range(lc):
            try:
                l_el[a].start = self._decimal(s+(dur*a))
                l_el[a].end = self._decimal(s+(dur*(a+1)))
            except AttributeError:
                continue
    def _new(self,struct,index,name,start,end,cont,elem,d_elem,metadata,
             det=False):
        if type(struct) == Corpus:                      # add Transcription
            struct.elem.insert(index,Transcription(name,start,end,
                                                   struct,metadata))
        elif type(struct) == Transcription:             # add Tier
            struct.elem.insert(index,Tier(name,start,end,struct,metadata))
        elif type(struct) == Tier:                      # add Segment
            struct.elem.insert(index,Segment(name,start,end,cont,struct,
                                            metadata))
        if not d_elem:                                  # d_elem
            d_elem = [index,None]
        struct.d_elem[struct.elem[index]] = d_elem
        self._fixIndexes(struct,index+1,len(self.elem))   # indexes
        return struct._retDet(struct.elem[index],det)
    def _copy(self,struct,index,elem,parent,ch_child,det):
        """Copies an already existing element 'elem' to 'struct'."""
        struct.elem.insert(index,elem.copy(struct))         # copy
        struct.d_elem[struct.elem[index]] = [index,parent]  # parent
        if ch_child:                                        # children
            l_struct = elem.struct.d_elem[elem][2:]
            struct.d_elem[elem] += l_struct.copy()
        self._fixIndexes(struct,index+1,len(struct.elem))   # indexes
        return self._retDet(struct.elem[index],det)
    def _rem(self,elem,index):
        l_children = elem.allChildren(det=True) # remove children
        for a in range(len(l_children)-1,-1,-1):
            n,i,child = l_children[a]
            if child.struct:
                child.struct._rem(child,i)
        elem.setParent(None)                    # warn parent
        if elem in self.d_elem:                 # remove from 'd_elem'
            self.d_elem.pop(elem)
            # Remove from 'elem' and update 'elem.struct'
        self.elem.pop(index); elem.struct = None
        self._fixIndexes(self,index,len(self))
        # Metadata functions
    def meta(self,key,div="omni",ch_list=False,empty=""):
        """Returns a (list of) string(s) for metadata values."""
        k = key; incr = 1
        if not div or div not in self.metadata:
            div = "omni"
        if (not div in self.metadata) or (not k in self.metadata[div]):
            return self._mdList([],ch_list,empty)
        else:
            return self._mdList(self.metadata[div][k],ch_list,empty)
    def getMeta(self,key,div="omni",ch_list=False,empty=""):
        """Just another function name for the same thing."""
        self.meta(key,div,ch_list,empty)
    def checkMeta(self,key,val="",div="omni",struct=None):
        """Checks a key (or value if set) in metadata."""
        struct = self._fixStruct(struct)
        if ((not div in struct.metadata) or
            (not key in struct.metadata[div])):
            return False
        if val and not val in struct.metadata[div][key]:
            return False
        else:
            return True
    def setMeta(self,key,val,div="omni",i=0):
        """Adds entry to metadata."""
        
        if div not in self.metadata:    # No subdivision
            self.metadata[div] = {}
        if key in self.metadata[div]:
            if i < 0 or i >= len(self.metadata[div][key]):
                self.metadata[div][key].append(val)
            else:
                self.metadata[div][key][i] = val
        else:
            self.metadata[div][key] = [val]
    def getMetaGroup(self,group="spk",div="omni",sym="_"):
        """Returns a dictionary of a given group (by prefix)."""
        
        if not div in self.metadata:
            return {}
        d_grp = {}; incr = 1; name = group+str(incr)
            # Get all items (using 'group' prefix) by index
        for key,l_val in self.metadata[div]:
            if key.startswith(group+sym):
                key = key.split(sym,1)[1]; d_tmp = {}
                for val in l_val:
                    k,val = val.split(sym,1)
                    d_tmp[k] = val
                if 'name' in d_tmp:
                    d_grp[d_tmp['name']] = d_tmp.copy()
                else:
                    d_grp[name] = d_tmp.copy(); incr += 1
                    name = group+str(incr)
        return d_grp
    def iterMeta(self,div="omni",ch_list=False):
        """Iterates over the metadata."""
        
        if not div:
            for sub,d_meta in self.metadata.items():
                for key,val in d_meta.items():
                    if not ch_list:
                        val = val[0]
                    yield (sub,key,val)
        elif not div in self.metadata:
            return
        else:
            for key,val in self.metadata[div].items():
                if not ch_list:
                    val = val[0]
                yield (key,val)
    
        # Structure functions
    def index(self):
        """Returns the object's index."""
        if self.struct and self in self.struct.d_elem:
            ind = self.struct.d_elem[self][0]
                # Object in 'elem' corresponds
            if self.struct.elem[ind] == self:
                return ind
                # We update the index in 'd_elem'
            elif self in self.struct.elem:
                ind = self.struct.elem.index(self)
                self.struct.d_elem[self][0] = ind
                return ind
        return -1
    def parent(self,det=False):
        """Returns the object's direct parent.
        If 'det' == True, returns a reference (name,index,pointer)."""
        if self.struct and self in self.struct.d_elem:
            return self._retDet(self.struct.d_elem[self][1],det)
        else:
            return self._retEmpty(det)
    def parents(self,struct=None,det=False):
        """Returns a list of the 'direct' object's parents.
        If 'det' == True, returns a reference (name,index,pointer)."""
        pobj = self.parent(); l_par = []
        while pobj:
            if (not struct) or pobj.struct == struct:
                l_par.append(self._retDet(pobj,det))
            pobj = pobj.parent()
        l_par.reverse()
        return l_par
    def parDict(self,struct=None,det=False):
        return self._parDict(self.parents(struct=struct,det=det),False)
    def allParents(self,struct=None,det=False):
        """Returns a list of all of the object's parents.
        If 'det' == True, returns a reference (name,index,pointer)."""
        l_par = self.parents(struct=struct,det=det)
            # Give highest parent's children (exclude 'self')
        if l_par:
            return [l_par[0]]+l_par[0].allChildren(stop=[self.struct],det=det)
        else:
            return []
    def allParDict(self,struct=None,det=False):
        return self._parDict(self.allParents(struct=struct,det=det),False)
    def iterPar(self,det=False):
        """Iterates over direct parent objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        self._iterstruct(self.parents(det))
    def iterAllPar(self,det=False):
        """Iterates over all parent objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        self._iterstruct(self.allParents(det))
    def children(self,struct=None,det=False):
        """Returns a list of the object's direct children.
        'struct' limits the direct children to those of that 'struct'."""

        l_tmp = []
        if self.struct and self in self.struct.d_elem:
            for el in self.struct.d_elem[self][2:]:
                if (not struct) or el.struct == struct:
                    l_tmp.append(self._retDet(el,det))
            return l_tmp
        else:
            return []
    def childDict(self,struct=None,det=False):
        """Returns 'children()' as a dictionary."""
        return self._childDict(self.children(struct=struct,det=det),False)
    def allChildren(self,stop=[],det=False):
        """Returns a list of all of the object's children."""
        l_child = []; ll_tmp = []
        ll_tmp.append((0,self.children()))
            # Iterate over all children
        while ll_tmp:
            ind,l_tmp = ll_tmp[-1]
                # End of that object's children
            if ind >= len(l_tmp):
                ll_tmp.pop(); continue
                # Increment
            cobj = l_tmp[ind]; ll_tmp[-1] = (ind+1,l_tmp)
            if cobj.struct in stop:
                continue
            l_child.append(self._retDet(cobj,det))
                # New child level
            if cobj.children():
                ll_tmp.append((0,cobj.children()))
        return l_child
    def allChildDict(self,struct=None,det=False):
        return self._childDict(self.allChidren(struct=struct,det=det),False)
    def iterChild(self,det=False):
        """Iterates over direct children objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        self._iterstruct(self.children(),det)
    def iterAllChild(self,stop=None,det=False):
        """Iterates over all children objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        self._iterstruct(self.allChildren(stop),det)
    def tree(self,det=False):
        """Returns a list of direct parent/children objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        return (self.parents(det=det)+[self._retDet(self,det=det)]
                +self.children(det=det))
    def allTree(self,det=False):
        """Returns a list of all parent/children objects.
        If 'det' == True, returns a reference (name,index,pointer)."""
        return (self.allParents(det=det)+[self._retDet(self,det=det)]
                +self.allChildren(det=det))

        # get functions
    def getSelf(self,det=False):
        """Returns itself."""
        return self._retDet(self,det)
    def findName(self,name,struct=None,det=False):
        """Gets an element by name (regular expression)."""
        struct = self._fixStruct(struct)
        for el in struct.elem:
            if re.search(name,el.name):
                return self._retDet(el,det)
        return self._retEmpty(det)
    def getName(self,name,struct=None,det=False):
        """Gets an element by name."""
        struct = self._fixStruct(struct)
        for el in struct.elem:
            if name == el.name:
                return self._retDet(el,det)
        return self._retEmpty(det)
    def getIndex(self,ind,struct=None,det=False):
        """Gets an element by index."""
        struct = self._fixStruct(struct)
        if ind >= 0 and ind < len(struct.elem):
            return struct._retDet(struct.elem[ind],det)
        return struct._retEmpty(det)
    def getTime(self,tcode,struct=None,det=False):
        """Gets an element by time code."""
        struct = self._fixStruct(struct)
        if not struct.elem:
            return struct._retDet(None,det)
            # Variables
        i_start = 0; i_end = len(struct.elem)-1; i_check = -1
        f_start = struct.elem[0].start; f_end = struct.elem[-1].end
        if f_start == f_end and tcode == f_end:
            return self._retDet(struct.elem[0],det)
        if tcode < f_start or tcode > f_end:
            return struct._retEmpty(det)
            # Loop
        while not i_start == i_end:
            if tcode < f_start or tcode >= f_end:
                return struct._retDet(None,det)
                # Weigh the next check
            i_check = (i_start +
                       int((i_end-i_start)*((tcode-f_start)/(f_end-f_start))))
            elem = struct.elem[i_check]
                # Found the right index
            if (tcode >= elem.start and (tcode < elem.end or
                (tcode == elem.end and elem.end == elem.start))):
                return struct._retDet(elem,det)
                # Is before that index
            elif tcode < elem.start:
                if i_check-1 >= i_start:
                    i_end = i_check-1; i_check = i_end
                    f_end = struct.elem[i_end].end
                # Is after that index
            elif tcode >= elem.end:
                if i_check+1 <= i_end:
                    i_start = i_check+1; i_check = i_start
                    f_start = struct.elem[i_start].start
            # Last loop (i_start == i_end case)
        elem = struct.elem[i_check]
        if tcode >= elem.start and tcode < elem.end:
            return struct._retDet(elem,det)
        return struct._retDet(None,det)
        # add functions
    def create(self,index=-1,name="",start=-1.,end=-1.,content="",elem=[],
               struct=None,d_elem={},metadata={},det=False):
        """Adds (creates) a new element to 'struct.elem'."""
        struct = self._fixStruct(struct); index = self._fixIndex(index)
        nel =  self._new(struct,index,name,start,end,content,elem,
                         d_elem,metadata,det)
        return nel
    def add(self,index=-1,elem=None,parent=None,
            ch_child=False,struct=None,det=False):
        """Adds (copies) a pre-existing object to 'struct.elem'."""
        if not elem:
            return self._retEmpty(det)
        struct = self._fixStruct(struct); index = self._fixIndex(index)
        nel = self._copy(struct,index,elem,parent,ch_child,det)
        return nel
        # set functions
    def move(self,index):
        """Moves the object within its structure's list of elements."""
            # Checks
        o_ind = self.index()
        if o_ind == index:                  # No need to move
            return index
        elif not self.struct:               # No structure mo move around
            return -1
        le = len(self.struct.elem)
        if index < 0 or index >= le:        # Append
            index = le
            # Move
        s = -1; e = -1
        self.struct.elem.insert(index,self) # Add new position
        if o_ind > index:
            o_ind += 1; s = index; e = o_ind
        else:
            s = o_ind; e = index+1
        self.struct.elem.pop(o_ind)         # Remove old position
        self._fixIndexes(self.struct,s,e)    # Fix indexes
        return index
    def remove(self,elem):
        """Removes an element by object (loses the structure)."""
            # Get index
        index = elem.index()
        if index < 0:
            return self._retEmpty(det)
            # Remove
        self._rem(elem,index)
    def pop(self,index,det=False):
        """Removes an element by index (loses the structure)."""
            # Get name
        if index < 0 or index >= len(self):
            return self._retEmpty(det)
        elem = self.elem[index]
            # Remove
        self._rem(elem,index)
        return self._retDet(elem,det)
    def remName(self,name,det=False):
        """Removes an element by name (loses the structure)."""
        n,index,elem = self.getName(name,det=True)
        if index < 0:           # empty
            return self._retEmpty(det)
        self._rem(elem,index)   # remove
        return self._retDet(elem,det)
        # set functions (for structure)
    def setParent(self,parent,old=True,new=True):
        if old and self.parent():                   # Deal with old parent
            self.parent().remChild(self,False,False)
        self.struct.d_elem[self][1] = parent        # Set parent
        if new and parent:                          # Deal with new parent
            parent.addChild(self,False,False)
    def addChild(self,child,old=True,new=True):
        if not child:
            return
        if old and child.parent():        # Deal with old parent
            child.parent().remChild(child,False,False)
        if (len(self.struct.d_elem[self]) <= 2 or
            (not child in self.struct.d_elem[self][2:])): # Add Child
            self.struct.d_elem[self].append(child)
        if new and child:                           # Deal with new parent
            child.setParent(self,False,False)
    def remChild(self,child,old=True,new=True):
        if (len(self.struct.d_elem[self]) <= 2 or   # Check
            child not in self.struct.d_elem[self][2:]):
            return
        tmp = self.struct.d_elem[self][2:]
        if old and child:                           # Deal with old parent
            child.setParent(None,False,False)
        for a in range(len(tmp)-1,-1,-1):           # Remove child
            if tmp[a] == child:
                tmp.pop(a)
        self.struct.d_elem[self] = self.struct.d_elem[self][:2]+tmp
    def clearChildren(self,old=True,new=True):
        if len(self.struct.d_elem[self]) <= 2:      # Check
            return
        if old:                                     # Deal with old parent
            for child in self.struct.d_elem[self][2:]:
                child.setParent(None,False,False)
        self.struct.d_elem[self] = self.struct.d_elem[self][:2]
    #### Main classes ####
    ######################

    #### SEGMENT ####
class Segment(Conteneur):
    """Class containing some text between two time codes."""
    
    def __init__(self,name="",start=-1.,end=-1.,content="",tier=None,
                 metadata={}):
            # See 'Conteneur' class for shared variables
        Conteneur.__init__(self,name,start,end,content,[],tier,{},metadata)
        
        # default functions
    def copy(self,tier=None):
        """Returns a copy of the Segment."""
        return Segment(self.name,self.start,self.end,self.content,
                       tier,self.metadata.copy())
    
        # navigation
    def segs():
        return self.elem
    def ti(self):
        """Returns self.tier's pointer."""
        if self.struct:
            return self.struct
        return None
    def tr(self):
        """Returns self.tier.trans's pointer."""
        if self.ti() and self.ti().struct:
            return self.ti().struct
        return None
    def co(self):
        """Returns the 'Corpus' instance."""
        if self.tr() and self.tr().struct:
            return self.tr().struct
        return None

        # set functions
    def setChildTime(self,ch=True):
        """Attributes time codes to child segments."""
        for ctier,l_csegs in self.childDict().items():
            if ch and l_csegs and l_csegs[0].start >= 0.:
                continue
            self._split(l_csegs,self)
    def cleanContent(self,l_elim=[],strip=""):
        """Trying to clean the segment's content as much as possible.
        ARGUMENTS:
        - 'l_elim'          : (lst<str>) list of sequences to be removed
        - 'strip'           : (str) set of characters to trim
        RETURNS:
        - Cleans the content."""
        
            # Replacing
        for elim in l_elim:
            self.content = self.content.replace(elim,"")
            # Trimming
        if strip:
            self.content = self.content.strip(strip)
        else:
            self.content = self.content.strip()

    #### TIER ####
class Tier(Conteneur):
    """Class containing a list of Segment instances."""

    def __init__(self,name="",start=-1.,end=-1.,trans=None,metadata={}):
            # See 'Conteneur' class for shared variables
        Conteneur.__init__(self,name,start,end,"",[],trans,{},metadata)
    
        # default functions
    def copy(self,trans=None,empty=False):
        cop = Tier(self.name,self.start,self.end,trans,
                    self.metadata.copy())
        if empty:
            return cop
        for seg in self.elem:
            nseg = cop.add(-1,seg.copy(cop))
            if seg.parent():
                nseg.setParent(seg.parent(),False,False)
            for child in seg.children():
                nseg.addChild(child,False,False)
        return cop

        # navigation
    def tr(self):
        """Returns self.trans's pointer."""
        if self.struct:
            return self.struct
        return None
    def co(self):
        """Returns self.trans.corpus' pointer."""
        if self.struct and self.tr().corpus:
            return self.tr().corpus
        return None

        # set functions
    def sortByTime(self):
        """Sorts the segments by time code.
        Note: let's not reinvent the wheel, we'll rely on 'sort()'."""
        def getStart(el):
            return el.start
        self.elem.sort(key=getStart)
        for a in range(len(self.elem)):
            self.d_elem[self.elem[a]][0] = a
    def fixOverlaps(self):
        """If two segments overlap, the former will be cut short.
        Note: if the overlap is caused by its parent, this will do nothing."""
        for a in range(len(self.elem)-1):
            seg1 = self.elem[a]; seg2 = self.elem[a+1]
            if seg1.end > seg2.start:
                seg1.end = seg2.start
    def fixGaps(self,sym="_"):
        """Adds segments in gaps."""
        
        ls = len(self)
        if self.elem and self.elem[-1].end < self.end:      # End
            self.create(ls,"a",self.elem[-1].end,self.end,sym)
        for a in range(ls-1,0,-1):                                  # Middle
            if self.elem[a-1].end < self.elem[a].start:
                self.create(a,"a",self.elem[a-1].end,
                            self.elem[a].start,sym)
        if self.elem and self.elem[0].start > self.start:   # Start
            self.create(0,"a",self.start,self.elem[0].start,sym)
    def remGaps(self,sym="_"):
        """Removes segments meant to be gaps."""
        
        for a in range(len(self)-1,-1,-1):
            seg = self.elem[a]
            if seg.content == sym:
                if seg.parent():
                    seg.parent().remChild(seg)
                self.elem.pop(a)
    def renameSegs(self,n="a",incr=0):
        """Renames every segment using 'n'+increment."""
        for a,seg in enumerate(self):
            seg.name = n+str(incr); incr += 1
        return incr
    def setChildTime(self,ch=True,stop=[]):
        """Sets segments' time codes for its children."""
        
        for child in self.allChildren(stop=stop):           # for each child
            if ch and child.elem and child.elem[0].start >= 0.:# check
                continue
            if stop and child in stop:                      # check stop
                continue
            l_segs = []; o_seg = None
            for cseg in child:                              # child segments
                pseg = cseg.parent()
                if not pseg == o_seg:                       # new parent
                    if o_seg and l_segs:
                        self._split(l_segs,o_seg)           # set time codes
                    o_seg = pseg; l_segs = []
                l_segs.append(cseg)                         # add segment
            if o_seg and l_segs:
                self._split(l_segs,o_seg)
    def symToDur(self,sym="_",syms="()"):
        """Turns segment content into duration."""
        for seg in self:
            if seg.content == sym:
                cont = "{:.03f}".format(seg.end-seg.start)
                if syms and len(syms) == 2:
                    cont = syms[0]+cont+syms[1]
                seg.content = cont
    def durToSym(self,sym="_",syms="()"):
        """Turns segment duration into symbol."""
        pattern = "\d+(|.\d+)"
        if syms and len(syms) == 2:
            pattern = syms[0]+pattern+syms[1]
        for seg in self:
            if re.match(pattern,seg.content):
                seg.content = sym

    #### TRANSCRIPTION ####
class Transcription(Conteneur):
    """Class containing a list of Tier instances."""

    def __init__(self,name="",start=-1.,end=-1.,corpus=None,metadata={}):
            # main variables
        Conteneur.__init__(self,name,start,end,"",[],corpus,{},metadata)
    
        # default functions
    def copy(self,corpus=None,empty=False):
        cop = Transcription(self.name,self.start,self.end,corpus,
                             self.metadata.copy())
        if empty:
            return cop
        d_cop = {None:None}
        for a,tier in enumerate(self):                      # elem
            pn,pi,ptier = tier.parent(det=True)
            d_cop[tier] = cop.add(-1,tier.copy(cop))
        for tier in self:                                   # tiers
            ntier = d_cop[tier]
            ptier = tier.parent(); nptier = d_cop[ptier]
            ntier.setParent(nptier)
            if not ptier:                                   # no parent
                continue
            for a,seg in enumerate(tier):                   # segments
                pn,pind,pseg = seg.parent(det=True)
                ntier.elem[a].setParent(nptier.elem[pind])
        return cop
    
        # Iter functions
    def iterSeg(self,det=False):
        """Iterates over all segments of the Transcription.
        Returns a reference (name,index,pointer) if 'det'."""
        for tier in self:
            for seg in tier:
                yield self._retDet(seg)
    def iterTime(self,det=False,settime=False):
        """Iterates over all segments in time order.
        Returns a reference (name,index,pointer) if 'det'."""
        if settime:
            self.setTime()
            # Set up the lists to parse tiers
        l_ind = []; l_max = []; max = -1.
        for tier in self:
            l_ind.append(0); l_max.append((tier,len(tier)))
            if tier.elem and time < tier.elem[-1].end:
                max = tier.elem[-1].end
        l_time = []; li = len(l_ind)
        if max < 0:
            raise StopIteration
            # Parse the tiers
        while True:
            time = max; nseg = None; pos = -1
            for a in range(li):
                    # Find the lowest time among (remaining) tier segments
                if l_ind[a] < l_max[a][1]:
                    ch = True; seg = l_max[a][0].elem[l_ind[a]]
                    if time > seg.start:
                        time = seg.start; nseg = seg; pos = a
                    # Increment past the exhausted segment
                if pos >= 0:
                    l_ind[a] = l_ind[a]+1
                    # Yield the segment
                if not nseg:
                    raise StopIteration
                else:
                    yield self._retDet(nseg)
        # navigation
    def co(self):
        return self.struct
    
        # get functions
    def getTop(self,det=False):
        """Returns all top tiers."""
        l_par = []
        for tier in self:
            if not tier.parent():
                l_par.append(self._retDet(tier,det))
        return l_par
    def getSpk(self,group="spk",div="omni",t_spk="speaker"):
        """We want all the speakers."""
            # Get what's in Transcription's metadata
        d_spk = {}
        if group and div:
            d_spk = self.getMetaGroup(group,div)
        if not t_spk:
            return d_spk
            # Get what's in the tiers
        l_none = []
        for tier in self:
            spk = tier.meta(t_spk,empty=None)
            if not spk:                             # No tier speaker
                l_none.append(tier); continue
            if spk not in d_spk:                    # New speaker
                d_spk[spk] = {'name':spk}
            if not 'tiers' in d_spk[spk]:           # No tier yet
                d_spk[spk]['tiers'] = [tier]
            else:
                d_spk[spk]['tiers'].append(tier)
        id = "spk"; incr = 1; n_spk = "spk1"        # Default speaker
        while n_spk in d_spk:
            incr += 1; n_spk = id+str(incr)
        d_spk[n_spk] = {'name':n_spk,'tiers':l_none}
        return d_spk
    
        # set functions
    def timetable(self):
        """Returns a list of ordered time boundaries from all Segments."""
            # Set up the lists to parse tiers
        l_time = []
        for tier in self:
            typ = tier.meta('type','tech')  # check type
            if typ and (not typ == "time" and not typ == "subtime"):
                continue
            for seg in tier:
                if seg.start not in l_time:
                    l_time.append(seg.start)
                if seg.end not in l_time:
                    l_time.append(seg.end)
        l_time.sort()
        return l_time
    def setBounds(self,allow=True):
        """Updates everyone to adopt the segments' lowest/highest times."""
        start,end = -1.,-1.
        for tier in self:
            s,e = -1.,-1.
            if tier.elem:
                s,e = tier.elem[0].start,tier.elem[-1].end
            if ((start < 0.) or (s < start)) and (allow or s >= 0.):
                start = s
            if (end < 0.) or (e > end):
                end = e
        for tier in self:
            tier.start = start; tier.end = end
        self.start = start; self.end = end
        return (start,end)
    def setChildTime(self,ch=True,stop=[]):
        """For each parent tier, sets time codes for the children.
        If 'ch', we limit that to tiers that don't yet have time codes."""
        
        l_par = self.getTop(); l_tmp = []           # put top tiers in 'l_par'
        while True:
            for ptier in l_par:                     # for each parent...
                l_tmp = l_tmp+ptier.children()
                ptier.setChildTime(ch=ch,stop=stop) # set time codes
            l_par = l_tmp.copy(); l_tmp.clear() # fill 'l_par' with children
            if not l_par:
                break
    def fixOverlaps(self):
        """If two segments overlap, the former will be cut short."""
        for tier in self:
            tier.fixOverlaps()
    def fixGaps(self,sym="_"):
        """Adds segments in gaps."""
        for tier in self:
            tier.fixGaps(sym)
    def remGaps(self,sym=["_"]):
        """Removes segments meant to be gaps."""
        for tier in self:
            tier.remGaps(sym)
    def renameSegs(self,n="a"):
        """Renames every segment using 'n'+increment."""
        incr = 0
        for tier in self:
            incr = tier.renameSegs(n,incr)
    
    #### CORPUS ####
class Corpus(Conteneur):
    """Class containing a list of Transcription instances."""

    def __init__(self,name=""):
            # main variables
        Conteneur.__init__(self,name,start,end,"",[],corpus,{},metadata)
        
        # default functions
    def copy(self):
        cop = Corpus(self.name)
        for trans in self.elem:
            ntrans = cop.add(-1,trans.copy(cop))

        # Iter functions
    def iterSeg(self,det=False):
        """Iterates over all segments of the Corpus.
        Returns a reference (name,index,pointer) for each segment."""
        for trans in self:
            for tier in trans:
                for seg in tier:
                    yield self._retDet(seg,det)
    def iterTier(self):
        """Iterates over all tiers of the Corpus.
        Returns a reference (name,index,pointer) for each segment."""
        for trans in self:
            for tier in trans:
                yield self._retDet(tier,det)
