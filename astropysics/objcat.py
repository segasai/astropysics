#Copyright (c) 2008 Erik Tollerud (etolleru@uci.edu) 

"""
This module contains objects and functions for generating catalogs of objects
where derived quantities are dynamically updated as they are changed.

The basic idea is a tree with the root always a Catalog object 

TODO: modules to also dynamically update via a web server.
*This package is currently under heavy development and subject to major change
without notice
"""

from __future__ import division
from math import pi
import numpy as np

try:
    #requires Python 2.6
    from abc import ABCMeta
    from abc import abstractmethod
    from abc import abstractproperty
    from collections import MutableSequence
except ImportError: #support for earlier versions
    abstractmethod = lambda x:x
    abstractproperty = property
    ABCMeta = type
    class MutableSequence(object):
        __slots__=('__weakref__',) #fake support for weakrefs

class _CatalogElement(object):
    pass

class Catalog(_CatalogElement):
    """
    This class represents a catalog of objects or catalogs.
    
    A Catalog is essentially a node in the object tree that does not contain 
    fields, but rather 
    """
    def __init__(self):
        super(Catalog,self).__init__()
        raise NotImplementedError
    
    
    

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
        return 'Source: ' + self._str
    
    
    
    
class Field(MutableSequence):
    """
    This class represents an attribute/characteristic/property of the
    CatalogObject it is associated with.  It stores the current value
    as well as all the other possible values.
    """
    __slots__=('name','type','value','_vals','_currenti')
    
    def __init__(self,name,type=None):
        """
        The field must have a name, and can optionally be given a type
                
        #TODO:auto-determine name from class
        """
        self.name = name
        self.type = type
        self._vals = []
        self._currenti = 0
        
    def __call__(self):
        return self.value
    
    def __len__(self):
        return len(self._vals)
    def __getitem__(self,key):
        if isinstance(key,basestring):
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
        elif isinstance(key,Source):
            for v in self._vals:
                if key==v.source:
                    return self._vals
        else:
            try:
                return self._vals[key]
            except TypeError:
                raise TypeError('Field keys must be strings or list indecies')
    def __setitem__(self,key,val):
        raise NotImplementedError
    def __delitem__(self,key):
        del self.vals[self._vals.index(self[key])]
    def insert(self,key,item):
        raise NotImplementedError
        
    def _getValue(self):
        try:
            return self._vals[self._currenti]
        except IndexError:
            raise IndexError('Field empty')
             #return None
    def _setValue(self,val):
        try:
            currval = self[val]
            self._currenti = self.index(currval)
        except KeyError:
            
            if not isinstance(val,FieldValue):
                raise ValueError('Tried to set a value that is not a FieldValue')
            self._vals.append(val)
            self._currenti = len(self._vals)-1
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
    
class FieldValue(object):
    __metaclass__ = ABCMeta
    __slots__ = ('source','dependson')
    
    @abstractmethod
    def __init__(self):
        self.source = None
        self.dependson = None
        
    value = abstractproperty()
    
    
class ObservedValue(FieldValue):
    """
    This value is a observed or otherwise measured value for the field
    with the associated Source.
    """
    __slots__=('_value')
    def __init__(self,value,source):
        super(ObservedValue,self).__init__()
        self.source = source
        self._value = value
    
    @property    
    def value(self):
        return self._value
        
class DerivedValue(FieldValue):
    """
    This value is derived from a set of other fields (possibly on other 
    objects).  Currently it does not support cycles (where e.g. 
    DerivedValue A depends on DerivedValue B which depends on A)
    """
    __slots__=('_f','_val')
    def __init__(self,func,dependson=None,source=None):
        super(DerivedValue,self).__init__()
        self.dependson = dependson
        self._f = f
        self._val = None
        self.source = source
        #TODO:more intelligently work out argument bindings
    @property
    def value(self):
        if self._val is None:
            self._val = self._f(*(field() for field in dependson))
        return self._val
    
    
class _CatalogObjectMeta(ABCMeta):
    def __call__(cls,*args,**kwargs):
        obj = ABCMeta.__call__(cls,*args,**kwargs)
        return obj

class CatalogObject(_CatalogElement):
    __metaclass__ = _CatalogObjectMeta
    
    def __init__(self):
        super(CatalogObject,self).__init__()
        raise NotImplementedError

    
del ABCMeta,abstractmethod,abstractproperty,MutableSequence #clean up namespace
  
