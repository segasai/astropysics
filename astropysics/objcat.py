#Copyright (c) 2008 Erik Tollerud (etolleru@uci.edu) 

"""
This module contains objects and functions for generating catalogs of objects
where derived quantities are dynamically updated as they are changed.

The basic idea is a tree/DAG with the root typically a Catalog object

TODO: modules to also dynamically update via a web server.
"""

from __future__ import division
from math import pi
import numpy as np

try:
    #requires Python 2.6
    from abc import ABCMeta
    from abc import abstractmethod
    from abc import abstractproperty
    from collections import Sequence,MutableSequence,MutableMapping
except ImportError: #support for earlier versions
    abstractmethod = lambda x:x
    abstractproperty = property
    ABCMeta = type
    class MutableSequence(object):
        __slots__=('__weakref__',) #support for weakrefs as necessary
    class MutableMapping(object):
        __slots__=('__weakref__',) #support for weakrefs as necessary
    class Sequence(object):
        __slots__=('__weakref__',) #support for weakrefs as necessary
        
class CycleError(Exception):
    """
    This exception indicates a cycle was detected in some graph-like structure
    """
    def __init__(self,message):
        super(CycleError,self).__init__(message)

class CatalogNode(object):
    """
    This Object is the superclass for all elements/nodes of a catalog.  
    This is an abstract class that must have its initializer overriden.
    
    Subclasses must call super(Subclass,self).__init__(parent) in their __init__
    """
    
    __metaclass__ = ABCMeta
    __slots__=('_parent','_children','__weakref__')
    
    @abstractmethod
    def __init__(self,parent):
        self._children = []
        self._parent = None
        
        if parent is not None:
            self.parent = parent
        
    def _cycleCheck(self,source):
        """
        call this from a child object with the child as the Source to check 
        for cycles in the graph
        """
        if source is self:
            raise CycleError('cycle detected in graph assignment attempt')
        if self._parent is None:
            return None
        else:
            return self.parent._cycleCheck(source)
            
    def _getParent(self):
        return self._parent
    def _setParent(self,val):
        
        if val is not None:
            val._cycleCheck(self) #TODO:test performance effect/make disablable
            val._children.append(self)
            
        if self._parent is not None:
            self._parent._children.remove(self)
        self._parent = val
        
    parent=property(_getParent,_setParent)
    
    
    @property
    def children(self):
        return tuple(self._children)
    
    def reorderChildren(self,neworder):
        """
        Change the order pf the children
        
        neworder can be either a sequence of  indecies (e.g. to reorder
        [a,b,c] to [c,a,b], neworder would be [2,0,1]), the string
        'reverse', or a function like the cmp keyword as would appear
        in the sorted builtin (can be None to do default sorting). 
        """
        if neworder == 'reverse':
            self._children.reverse()
        elif callable(neworder):
            self._children.sort(cmp=neworder)
        else: #TODO:faster way to do this if necessary?
            if len(neworder) != len(self._children):
                raise ValueError('input sequence does not have correct number of elements')
            
            added = np.zeros(len(self._children),dtype=bool)
            newl = []
            for i in neworder:
                if added[i]:
                    raise ValueError('input sequence has repeats')
                newl.append(self._children[i])
                added[i] = True
                
    @property
    def nnodes(self):
        """
        this gives the number of total nodes at this point in the tree
        (including self - e.g. a leaf in the tree returns 1)
        """
        return sum([c.nnodes for c in self._children],1)
        
    
    def visit(self,func,traversal='postorder'):
        """
        This function walks through the object and all its children, 
        executing func(CatalogNode)
        
        traversal is the traversal order of the tree - can be 'preorder',
        'postorder', a number indicating at which index the root
        should be evaluated (pre/post are 0/-1), or 'level'/'breathfirst' 
        """
        if type(traversal)==int:
            retvals = []
            doroot = True
            for i,c in enumerate(self._children):
                if i == traversal:
                    retvals.append(func(self))
                    doneroot = False
                retvals.extend(c.visit(func,traversal))
            if doroot:
                retvals.append(func(self))
                
        elif traversal is None: #None means postorder
            retvals = []
            for c in self._children:
                retvals.extend(c.visit(func,traversal))
            retvals.append(func(self))    
            
        elif traversal == 'postorder':
            retvals = self.visit(func,None)
        elif traversal == 'preorder':
            retvals = self.visit(func,0)
        elif traversal == 'level' or traversal == 'breadthfirst':
            from collections import deque
            
            retvals=[]
            q = deque()
            q.append(self)
            while len(q)>0:
                elem = q.popleft()
                retvals.append(func(elem))
                q.extend(elem._children)
#        elif traversal == 'reverselevel' or traversal == 'reversebreadthfirst':
#            from collections import deque
            
#            elems=[]
#            q = deque()
#            q.append(self)
#            while len(q)>0:
#                elem = q.popleft()
#                elems.insert(0,elem)
#                q.extend(elem._children)
#            retvals = [func(e) for e in elems]
        else:
            raise ValueError('unrecognized traversal type')
        
        return retvals
    
class FieldNode(CatalogNode,MutableMapping,Sequence):
    """
    A node in the catalog that has Fields.  This is an abstract class that 
    must have its initializer overriden.
    
    Note that for these subclasses, attribute access (e.g. node.fieldname) 
    accesses the Field object, while mapping or sequence-style access 
    (e.g node['fieldname'] or node[1])  directly accesses the current value
    of the field (or None if there is no value)
    """
    __slots__=('_fieldnames',)
    
    @abstractmethod
    def __init__(self,parent):
        super(FieldNode,self).__init__(parent)
        self._fieldnames = []
        
    def addField(self,field):
        if not isinstance(field,Field):
            raise ValueError('input value is not a Field')
        if field.name in self._fieldnames:
            raise ValueError('Field name "%s" already present'%field.name)
        setattr(self,field.name,field)
        self._fieldnames.append(field.name)
        
    def delField(self,fieldname):
        try:
            self._fieldnames.remove(fieldname)
            if hasattr(self.__class__,fieldname):
                setattr(self,fieldname,None)
            else:
                delattr(self,fieldname)
        except ValueError:
            raise KeyError('Field "%s" not found'%fieldname)
        
    #def __iter__(self):
    #    return iter(self._fieldnames)
    
    def __len__(self):
        return len(self._fieldnames)
    
    def __contains__(self,key):
        return key in self._fieldnames
        
    def __getitem__(self,key):
        if key not in self._fieldnames:
            try:
                key = self._fieldnames[key]
            except (IndexError,TypeError):
                raise KeyError('Field "%s" not found'%key)
        try:
            return getattr(self,key).value()
        except IndexError: #field empty
            return None
    
    def __setitem__(self,key,val):
        if key not in self._fieldnames:
            try:
                key = self._fieldnames[key]
            except (IndexError,TypeError):
                raise KeyError('Field "%s" not found'%key)
        field = getattr(self,key)
        field.value = val
    
    def __delitem__(self,key):
        self.delField(key)
        
    @property
    def fieldnames(self):
        return tuple(self._fieldnames)
    
    #TODO: overwrite __setattr__ and __delattr__ to respond better to Field objects
   
#<----------------------------node attribute types----------------------------->    

class _SourceMeta(type):
    #TODO: improve Source Singletons
    def __call__(cls,*args,**kwargs):
        obj = type.__call__(cls,*args,**kwargs)
        if not obj._str in Source._singdict:
            Source._singdict[obj._str] = obj
        return Source._singdict[obj._str]

class Source(object):
    __metaclass__ = _SourceMeta
    _singdict = {}
    
    def __init__(self,src):
        self._str = str(src)
        
    def __str__(self):
        return 'Source ' + self._str
    
class Field(MutableSequence):
    """
    This class represents an attribute/characteristic/property of the
    CatalogObject it is associated with.  It stores the current value
    as well as all the other possible values.
    
    note that while the value property will return a FieldValue 
    object (or None), calling the Field directly returns the 
    value attribute of the current FieldValue 
    """
    __slots__=('_name','_type','_vals','_currenti')
    
    def __init__(self,name,type=None,defaultValue=None):
        """
        The field must have a name, and can optionally be given a type
                
        #TODO:auto-determine name from class
        """        
        self._name = name
        self._vals = []
        self._currenti = 0
        self._type = None
        
        self.type = type
        self.defaultValue = defaultValue
        
    def __call__(self):
        return self.value.value
    def __len__(self):
        return len(self._vals)
    
    def __str__(self):
        return 'Field %s:[%s]'%(self._name,', '.join([str(v) for v in self._vals]))
    
    def _checkValue(self,val,checkdup=True):
        if not (isinstance(val,FieldValue) or (hasattr(val,'source') and hasattr(val,'value'))):
            raise TypeError('Input not FieldValue-compatible')
        if self.type is not None:
            if isinstance(self.type,np.dtype):
                if not isinstance(val.value,np.ndarray):
                    raise TypeError('Value %s not a numpy array'%val)
                if val.value.dtype != self.type:
                    raise TypeError('Array %s does not match dtype %s'%(val,self.type))
            elif not isinstance(val.value,self.type):
                raise TypeError('Value %s is not of type %s'%(val,self.type))
            
        if checkdup:
            for v in self._vals:
                if v.source is val.source:
                    raise ValueError('value with source %s already present in Field'%v.source)
        
    def __getitem__(self,key):
        if isinstance(key,Source):
            for v in self._vals:
                #TODO: == compared to "is" performance tests
                if key==v.source:
                    return v
            raise KeyError('Could not find requested Source')
        elif isinstance(key,FieldValue):
            for v in self._vals:
                if key==v:
                    return v
            raise KeyError('Could not find requested FieldValue')
        elif isinstance(key,basestring):
            if 'depends' in key.lower():
                depre = key.lower().replace('depends','').strip()
                if depre=='':
                    depnum=0
                else:
                    depnum=int(depre)
                try:
                    return [v for v in self._vals if v.depends is not None][depnum]
                except IndexError:
                    raise IndexError('dependent value key %i does not exist'%depnum)
            else:
                #TODO:test performance loss
                return self.__getitem__(Source(key))
        else:
            try:
                return self._vals[key]
            except TypeError:
                raise TypeError('Field keys must be strings or list indecies')
    def __setitem__(self,key,val):
        self._checkValue(val)
        i = self._vals.index(self[key])
        self._vals[i] = val
        
    def __delitem__(self,key):
        del self.vals[self._vals.index(self[key])]
    def insert(self,key,val):
        self._checkValue(val)
        if key == len(self._vals):
            i = len(self._vals)
        else:
            i = self._vals.index(self[key])
        self._vals.insert(i,val)
        if self._currenti >= i and len(self._vals) != 1:
            self._currenti += 1
        
    def _getValue(self):
        try:
            return self._vals[self._currenti]
        except IndexError:
            if self._defaultValue is None:
                raise IndexError('Field empty')
            else:
                return self._defaultValue
    def _setValue(self,val):
        #TODO: decide if this try/except layering is too performance intensive
        try:
            self._currenti = self.index(self[val])
        except (TypeError,KeyError):
            #TODO: consider if it's really a good idea to allow tuple-specification
            if type(val) is tuple and self.type is not tuple:
                val = ObservedValue(*val)
            try:
                self._checkValue(val)
                
                self._vals.append(val)
                self._currenti = len(self._vals)-1
            
            except TypeError:
                if len(self) == 0:
                    self.defaultValue = val
            
    def _delValue(self):
        try:
            del self._vals[self._currenti]
            self._currenti = 0
        except IndexError:
            raise IndexError('deleting from empty Field')
    value = property(_getValue,_setValue,_delValue,
    """
    The current value can be set by setting to a Source object,
    a string matching a Source, or a new FieldValue (adding the value and
    setting it as current.  The current value can also be deleted
    or retrieved using this property
    """)
    
    @property
    def values(self):
        """
        the FieldValue objects in this Field
        """
        return tuple(self._vals)
    
    def _getType(self):
        return self._type
    def _setType(self,val):
        if val is None:
            self._type = None
        else:
            oldt = self._type
            self._type = val
            try:
                for v in self._vals:
                    self._checkValue(v,checkdup=False)
            except:
                self._type = oldt
                raise
    type = property(_getType,_setType,doc="""
    Selects the type to enforce for this field.  
    if None, no type-checking will be performed
    if a numpy dtype, the value must be an array matching the dtype
    """)
    
    def _getDefault(self):
        if self._defaultValue is None:
            return None
        return self._defaultValue.value
    def _setDefault(self,val):
        if val is None:
            defval = None
        else:
            defval=ObservedValue(val,source=None)
            try:
                self._checkValue(defval,False)
            except:
                raise TypeError('Invalid default value of type %s, expected %s'%(type(val),self.type))
        self._defaultValue = defval
    defaultValue = property(_getDefault,_setDefault,doc="""
    Default value if the field is empty.  Must match the type if specified.
    """)
    
    @property
    def name(self):
        return self._name

#<------------------------------Node types------------------------------------->

class Catalog(CatalogNode):
    """
    This class represents a catalog of objects or catalogs.
    
    A Catalog is essentially a node in the object tree that does nothing other 
    than must act as a root.
    """    
    def __init__(self,name='default Catalog'):
        super(Catalog,self).__init__(parent=None)
        self.name = name
    
    @property
    def parent(self):
        return None    
    
    #these methods allow support for doing uniform mapping-like lookups over a catalog
    def __contains__(self,key):
        return hasattr(self,key)
    def __getitem__(self,key):
        return getattr(self,key)
    
    
class FieldValue(object):
    __metaclass__ = ABCMeta
    __slots__ = ('_source')
    
    @abstractmethod
    def __init__(self):
        self._source = None
    
    value = abstractproperty()
    
    def _getSource(self):
        return self._source
    def _setSource(self,val):
        if not (val is None or isinstance(val,Source)):
            try:
                val = Source(val)
            except: 
                raise TypeError('Input source is not convertable to a Source object')
        self._source = val 
    source=property(_getSource,_setSource)
    
    def __call__(self):
        return self.value
    
    def __str__(self):
        return str(self.value)
    
class ObservedValue(FieldValue):
    """
    This value is a observed or otherwise measured value for the field
    with the associated Source.
    """
    __slots__=('_value')
    def __init__(self,value,source):
        super(ObservedValue,self).__init__()
        if not isinstance(source,Source):
            source = Source(source)
        self.source = source
        self._value = value
        
    def __str__(self):
        return '%s:%s'%(self.value,self.source)
    
    @property    
    def value(self):
        return self._value
        
class DerivedValue(FieldValue):
    """
    This value is derived from a set of other fields (possibly on other 
    objects).  Currently it does not support cycles (where e.g. 
    DerivedValue A depends on DerivedValue B which depends on A)
    """
    __slots__=('_f','_val','dependson')
    def __init__(self,func,dependson=None,source=None):
        """
        The supplied function will be used with the sequence of Field's
        that the values for the derived value are to work with. 
        
        alternatively, if depndson is None, the  depndencies will be 
        inferred from the default values of the 
        """
        super(DerivedValue,self).__init__()
        
        from weakref import ref
        
        if dependson is None:
            from inspect import getargspec
            args,varargs,varkw,defaults = getargspec(func)
            if len(args) != len(defs) or varargs or varkw:
                raise ValueError('input function does not have all defaults \
                                  matched to dependencies or has varargs')
            dependson = defaults 
        #TODO:infer dependencies from argument names and parents/self fields
        
        
        self.dependson = []
        for dep in dependson:
            if not isinstance(dep,Field):
                raise ValueError('provided dependencies are not Fields')
            self.dependson.append(ref(dep))
        
        self._f = func
        self._val = None
        self.source = source
        #TODO:more intelligently work out argument bindings
    
    def __str__(self):
        return '%s:Derived'%self.value
        
    @property
    def value(self):
        if self._val is None:
            self._val = self._f(*(fieldwr()() for fieldwr in self.dependson))
            #TODO:check for bad wrs?
        return self._val
    
    @staticmethod
    def derivedFunc(func):
        """
        Use this as a decorator to convert a function with defaults into
        a DerivedValue instance with the defaults as the dependencies
        """
        from inspect import getargspec
        args,varargs,kwds,defs=getargspec(func)
        if len(args) != len(defs) or varargs or kwds:
            raise ValueError('input function does not have all defaults \
                              matched to dependencies or has varargs')
        return DerivedValue(func,dependson=defs)
        
    
    
    
#class _CatalogObjectMeta(ABCMeta):
#    def __call__(cls,*args,**kwargs):
#        obj = super(_CatalogObjectMeta,cls).__call__(*args,**kwargs)
#        return obj

class CatalogObject(FieldNode):
    """
    This class represents a FieldNode in the catalog that follows a particular
    data structure (i.e. a consistent set of Fields).  It is meant to be
    subclassed to define generic types of objects in the catalog.
    
    The fields and names are inferred from the class definition and 
    hence the class attribute name must match the field name.  Any 
    FieldValues present in the class objects will be ignored
    """
    #__metaclass__ = _CatalogObjectMeta
    
    def __init__(self,parent):
        import inspect
        
        super(CatalogObject,self).__init__(parent)
        self._altered = False
        
        #apply Fields from class into new object as new Fields
        for k,v in inspect.getmembers(self.__class__,lambda x:isinstance(x,Field)): #TODO:faster way than lambda?
            if v.name != k: #TODO: figure out if this can be done at "compile-time"
                raise KeyError('Name of Field (%s) does not match name in class attribute (%s)'%(v.name,k))
            fobj = Field(v.name,v.type,None if v.defaultValue is None else v.defaultValue.value)
            setattr(self,k,fobj)
            self._fieldnames.append(k)
            
         
    
    @property
    def altered(self):
        """
        If True, the object no longer matches the specification given by the 
        class.  Note that this will remain True even if the offending fields
        are returned to their correct state.
        """
        return self._altered
    
    def revert(self):
        """
        Revert this object back to the standard Fields for  the class.
        Any deleted fields will be populated with the class Default Value
        any attributes that match the names of deleted Fields will be 
        overwritten
        
        TODO:test
        """
        import inspect
        import new
        
        #replace any deleted Fields with defaults and keep track of which should be kept
        fields=[]
        for k,v in inspect.getmembers(self.__class__,lambda x:isinstance(x,Field)):
            fields.append(k)
            if not hasattr(self,k) or not isinstance(getattr(self,k),Field):
                fobj = Field(name=v.name,type=v.type,defaultValue=v.defaultValue)
                setattr(self,k,fobj)
                
        for k,v in inspect.getmembers(self,lambda x:isinstance(x,Field)):
            if k not in fields:
                delattr(self,k)
                
        self._fieldnames = fields
        self._altered = False
        self.addField = new.instancemethod(CatalogObject.addField,self,CatalogObject)
        self.delField = new.instancemethod(CatalogObject.delField,self,CatalogObject)
    
    def addField(self,field):
        self._altered = True
        self.addField = super(CatalogObject,self).addField
        self.addField(field)
        
    def delField(self,fieldname):
        self._altered = True
        self.delField = super(CatalogObject,self).delField
        self.delField(fieldname)
        
        
#<--------------------builtin catalog types------------------------------------>

class AstronomicalObject(CatalogObject):
    from .coords import AngularPosition
    
    def __init__(self,parent=None,name='default Name'):
        super(AstronomicalObject,self).__init__(parent)
        self.name.defaultValue=name
        
    _fieldorder = ('name','loc')
    name = Field('name',basestring)
    loc = Field('loc',AngularPosition)
    
    
del ABCMeta,abstractmethod,abstractproperty,MutableSequence,pi,division #clean up namespace
  
