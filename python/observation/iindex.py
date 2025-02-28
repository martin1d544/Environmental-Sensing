# -*- coding: utf-8 -*-
"""
Created on Thu May 26 20:30:00 2022

@author: philippe@loco-labs.io

The `observation.iindex` module contains the `Iindex` class.

Documentation is available in other pages :

- The Json Standard for Iindex is defined [here](https://github.com/loco-philippe/
Environmental-Sensing/tree/main/documentation/IlistJSON-Standard.pdf)
- The concept of 'indexed list' is described in
[this page](https://github.com/loco-philippe/Environmental-Sensing/wiki/Indexed-list).
- The non-regression tests are at [this page](https://github.com/loco-philippe/
Environmental-Sensing/blob/main/python/Tests/test_iindex.py)
- The [examples](https://github.com/loco-philippe/Environmental-Sensing/tree/main/
python/Examples/Iindex) are :
    - [creation](https://github.com/loco-philippe/Environmental-Sensing/blob/main/
    python/Examples/Iindex/Iindex_creation.ipynb)
    - [value](https://github.com/loco-philippe/Environmental-Sensing/blob/main/
    python/Examples/Iindex/Iindex_value.ipynb)
    - [update](https://github.com/loco-philippe/Environmental-Sensing/blob/main/
    python/Examples/Iindex/Iindex_update.ipynb)
    - [structure](https://github.com/loco-philippe/Environmental-Sensing/blob/main/
    python/Examples/Iindex/Iindex_structure.ipynb)
    - [structure-analysis](https://github.com/loco-philippe/Environmental-Sensing/
    blob/main/python/Examples/Iindex/Iindex_structure-analysis.ipynb)

---
"""
# %% declarations
from copy import copy, deepcopy

from esconstante import ES
from esvalue_base import ESValue
from iindex_interface import IindexInterface, IindexError
from iindex_structure import IindexStructure
from util import util


class Iindex(IindexStructure, IindexInterface):
    # %% intro
    '''
    An `Iindex` is a representation of an index list .

    *Attributes (for dynamic attributes see @property methods)* :

    - **name** : name of the Iindex
    - **codec** : list of values for each key
    - **keys** : list of code values

    The methods defined in this class are :

    *constructor (@classmethod)*

    - `Iindex.dic`
    - `Iindex.ext`
    - `Iindex.obj`
    - `Iindex.from_parent`
    - `Iindex.from_obj`
    - `Iindex.merging`

    *dynamic value (getters @property)*

    - `Iindex.values`
    - `Iindex.val`
    - `Iindex.cod`
    - `Iindex.infos`

    *add - update methods (`observation.iindex_structure.IindexStructure`)*

    - `Iindex.append`
    - `Iindex.setcodecvalue`
    - `Iindex.setcodeclist`
    - `Iindex.setname`
    - `Iindex.setkeys`
    - `Iindex.setlistvalue`
    - `Iindex.setvalue`

    *transform methods (`observation.iindex_structure.IindexStructure`)*

    - `Iindex.coupling`
    - `Iindex.extendkeys`
    - `Iindex.full`
    - `Iindex.reindex`
    - `Iindex.reorder`
    - `Iindex.sort`
    - `Iindex.tocoupled`
    - `Iindex.tostdcodec`

    *getters methods (`observation.iindex_structure.IindexStructure`)*

    - `Iindex.couplinginfos`
    - `Iindex.derkeys`
    - `Iindex.getduplicates`
    - `Iindex.iscrossed`
    - `Iindex.iscoupled`
    - `Iindex.isderived`
    - `Iindex.islinked`
    - `Iindex.isvalue`
    - `Iindex.iskeysfromderkeys`
    - `Iindex.keysfromderkeys`
    - `Iindex.keytoval`
    - `Iindex.loc`
    - `Iindex.recordfromkeys`
    - `Iindex.recordfromvalue`
    - `Iindex.valtokey`

    *export methods (`observation.iindex_interface.IindexInterface`)*

    - `Iindex.json`
    - `Iindex.to_obj`
    - `Iindex.to_dict_obj`
    - `Iindex.to_numpy`
    - `Iindex.to_pandas`
    - `Iindex.vlist`
    - `Iindex.vName`
    - `Iindex.vSimple`
    '''

    def __init__(self, codec=None, name=None, keys=None, typevalue=ES.def_clsName,
                 lendefault=0, reindex=False, castobj=True):
        '''
        Iindex constructor.

        *Parameters*

        - **codec** :  list (default None) - external different values of index (see data model)
        - **keys** :  list (default None)  - key value of index (see data model)
        - **name** : string (default None) - name of index (see data model)
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec
        - **lendefault** : integer (default 0) - default len if no keys is defined
        - **reindex** : boolean (default True) - if True, default codec is apply'''
        if isinstance(codec, Iindex):
            self._keys = copy(codec._keys)
            self._codec = deepcopy(codec._codec)
            self.name = copy(codec.name)
            return
        if codec is None:
            codec = []
        if not isinstance(codec, list):
            codec = [codec]
        leng = lendefault
        if codec and len(codec) > 0 and not leng:
            leng = len(codec)
        if not keys is None:
            leng = len(keys)
        if not name:
            name = ES.defaultindex
        typevalue = util.typename(name, typevalue)
        if not (keys is None or isinstance(keys, list)):
            raise IindexError("keys not list")
        if keys is None and leng == 0:
            keys = []
        elif keys is None:
            keys = [(i*len(codec))//leng for i in range(leng)]
        if not isinstance(codec, list):
            raise IindexError("codec not list")
        if codec == []:
            codec = util.tocodec(keys)
        if not typevalue is None or castobj:
            codec = util.castobj(codec, typevalue)
        self._keys = keys
        self._codec = codec
        self.name = name
        if reindex:
            self.reindex()

    @classmethod
    def dic(cls, dicvalues=None, typevalue=ES.def_clsName, fullcodec=False):
        '''
        Iindex constructor (external dictionnary).

        *Parameters*

        - **dicvalues** : {name : values}  (see data model)
        - **fullcodec** : boolean (default False) - full codec if True
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec'''
        if not dicvalues:
            return cls.ext(name=None, values=None, typevalue=typevalue, fullcodec=fullcodec)
        if isinstance(dicvalues, Iindex):
            return copy(dicvalues)
        if not isinstance(dicvalues, dict):
            raise IindexError("dicvalues not dict")
        if len(dicvalues) != 1:
            raise IindexError("one key:values is required")
        name = list(dicvalues.keys())[0]
        values = dicvalues[name]
        return cls.ext(name=name, values=values, typevalue=typevalue, fullcodec=fullcodec)

    @classmethod
    def ext(cls, values=None, name=None, typevalue=ES.def_clsName, fullcodec=False):
        '''
        Iindex constructor (external list).

        *Parameters*

        - **values** :  list (default None) - external values of index (see data model)
        - **name** : string (default None) - name of index (see data model)
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec
        - **fullcodec** : boolean (default False) - full codec if True'''
        if not values:
            return cls(name=name, typevalue=typevalue)
        if isinstance(values, Iindex):
            return copy(values)
        if not isinstance(values, list):
            values = [values]
        typevalue = util.typename(name, typevalue)
        values = util.castobj(values, typevalue)
        if fullcodec:
            codec, keys = (values, list(range(len(values))))
        else:
            codec, keys = util.resetidx(values)
        return cls(codec=codec, name=name, keys=keys, typevalue=None, castobj=False)

    @classmethod
    def from_parent(cls, codec, parent, name=None, typevalue=ES.def_clsName, reindex=False):
        '''Generate an Iindex Object from specific codec and parent keys.

        *Parameters*

        - **codec** : list of objects
        - **name** : string (default None) - name of index (see data model)
        - **parent** : Iindex, parent of the new Iindex
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec
        - **reindex** : boolean (default True) - if True, default codec is apply

        *Returns* : Iindex '''
        if isinstance(codec, Iindex):
            return copy(codec)
        return cls(codec=codec, name=name, keys=parent._keys, typevalue=typevalue, reindex=reindex)

    @classmethod
    def from_obj(cls, bsd, extkeys=None, typevalue=ES.def_clsName, context=True, reindex=False):
        '''Generate an Iindex Object from a bytes, json or dict value and from
        a keys list (derived Iindex)

        *Parameters*

        - **bs** : bytes, string or dict data to convert
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec
        - **extkeys** : list (default None) of int, string or dict data to convert in keys
        - **context** : boolean (default True) - if False, only codec and keys are included
        - **reindex** : boolean (default False) - if True, default codec is apply

        *Returns* : tuple(code, Iindex) '''
        if isinstance(bsd, Iindex):
            return (ES.nullparent, copy(bsd))
        name, typevaluedec, codec, parent, keys, isfullindex, isparent, isvar =\
            Iindex.decodeobj(bsd, typevalue, context)
        if extkeys and parent >= 0:
            keys = Iindex.keysfromderkeys(extkeys, keys)
        elif extkeys and parent < 0:
            keys = extkeys
        if keys is None:
            keys = list(range(len(codec)))
        if typevaluedec:
            typevalue = typevaluedec
        return (parent, cls(codec=codec, name=name, keys=keys, typevalue=typevalue,
                            reindex=reindex))

    @classmethod
    def from_dict_obj(cls, bsd, typevalue=ES.def_clsName, reindex=False):
        '''Generate an Iindex Object from a dict value'''
        var = False
        if not isinstance(bsd, dict):
            raise IindexError('data is not a dict')
        name = list(bsd.keys())[0]
        bsdv = list(bsd.values())[0]
        if not 'value' in bsdv:
            raise IindexError('value is not present')
        value = bsdv['value']
        if not isinstance(value, list):
            value = [value]
        if 'type' in bsdv and isinstance(bsdv['type'], str):
            typevalue = bsdv['type']
        if 'var' in bsdv and isinstance(bsdv['var'], bool):
            var = bsdv['var']
        codec = [util.castval(val['codec'], typevalue) for val in value]
        pairs = []
        for i, rec in enumerate(value):
            record = rec['record']
            if not isinstance(record, list):
                record = [record]
            for j in record:
                pairs.append((j, i))
        if not pairs:
            return (var, cls())
        keys = list(list(zip(*sorted(pairs)))[1])

        idx = cls(name=name, codec=codec, keys=keys, typevalue=None)
        return (var, idx)

    @classmethod
    def merging(cls, listidx, name=None):
        '''Create a new Iindex with values are tuples of listidx Iindex values

        *Parameters*

        - **listidx** : list of Iindex to be merged.
        - **name** : string (default : None) - Name of the new Iindex

        *Returns* : new Iindex'''
        if not name:
            name = str(list({idx.name for idx in listidx}))
        values = util.tuple(util.transpose([idx.values for idx in listidx]))
        return cls.ext(values, name)

    @classmethod
    def obj(cls, bsd, extkeys=None, typevalue=ES.def_clsName, context=True, reindex=False):
        '''Generate an Iindex Object from a bytes, json or dict value and from
        a keys list (derived Iindex)

        *Parameters*

        - **bsd** : bytes, string or dict data to convert
        - **typevalue** : string (default ES.def_clsName) - typevalue to apply to codec
        - **extkeys** : list (default None) of int, string or dict data to convert in keys
        - **context** : boolean (default True) - if False, only codec and keys are included
        - **reindex** : boolean (default True) - if True, default codec is apply

        *Returns* : tuple(code, Iindex) '''
        if isinstance(bsd, dict):
            return cls.from_dict_obj(bsd, typevalue=typevalue, reindex=reindex)[1]
        return cls.from_obj(bsd, extkeys=extkeys, typevalue=typevalue,
                            context=context, reindex=reindex)[1]


# %% special


    def __repr__(self):
        '''return classname and number of value'''
        return self.__class__.__name__ + '[' + str(len(self)) + ']'

    def __str__(self):
        '''return json string format'''
        return '    ' + self.to_obj(encoded=True, modecodec='full', untyped=False) + '\n'

    def __eq__(self, other):
        ''' equal if class and values are equal'''
        return self.__class__ .__name__ == other.__class__.__name__ and self.values == other.values

    def __len__(self):
        ''' len of values'''
        return len(self._keys)

    def __contains__(self, item):
        ''' item of values'''
        return item in self.values

    def __getitem__(self, ind):
        ''' return value item (value conversion)'''
        if isinstance(ind, tuple):
            return [copy(self.values[i]) for i in ind]
        #return self.values[ind]
        return copy(self.values[ind])

    def __setitem__(self, ind, value):
        ''' modify values item'''
        if ind < 0 or ind >= len(self):
            raise IindexError("out of bounds")
        self.setvalue(ind, value, extern=True)

    def __delitem__(self, ind):
        '''remove a record (value and key).'''
        self._keys.pop(ind)
        self.reindex()

    def __hash__(self):
        '''return hash(codec) + hash(keys)'''
        return hash(tuple(self.values))

    def _hashe(self):
        '''return hash(values)'''
        return hash(tuple(self.values))

    def _hashi(self):
        '''return hash(codec) + hash(keys)'''
        return hash(tuple(self._codec)) + hash(tuple(self._keys))

    def __add__(self, other):
        ''' Add other's values to self's values in a new Iindex'''
        newiindex = self.__copy__()
        newiindex.__iadd__(other)
        return newiindex

    def __iadd__(self, other):
        ''' Add other's values to self's values'''
        return self.add(other, solve=False)

    def add(self, other, solve=True):
        ''' Add other's values to self's values

        *Parameters*

        - **other** : Iindex object to add to self object
        - **solve** : Boolean (default True) - If True, replace None other's codec value
        with self codec value.

        *Returns* : self '''
        if solve:
            solved = copy(other)
            for i in range(len(solved._codec)):
                if not util.isNotNull(solved._codec[i]) and i in range(len(self._codec)):
                    solved._codec[i] = self._codec[i]
            values = self.values + solved.values
        else:
            values = self.values + other.values
        codec = util.tocodec(values)
        if set(codec) != set(self._codec):
            self._codec = codec
        self._keys = util.tokeys(values, self._codec)
        return self

    def __copy__(self):
        ''' Copy all the data '''
        return Iindex(self)

# %% property
    @property
    def cod(self):
        '''return codec conversion to string '''
        return self.to_obj(modecodec='optimize', codecval=True, encoded=False, listunic=True)

    @property
    def codec(self):
        '''return codec  '''
        return self._codec

    @property
    def infos(self):
        '''return dict with lencodec, typecodec, ratecodec, mincodec, maxcodec'''
        maxi = len(self)
        mini = len(set(self._codec))
        xlen = len(self._codec)
        rate = 0.0
        if maxi == 0:
            typecodec = 'null'
        elif xlen == 1:
            typecodec = 'unique'
        elif mini == maxi:
            typecodec = 'complete'
        elif xlen == maxi:
            typecodec = 'full'
        else:
            rate = (maxi - xlen) / (maxi - mini)
            if xlen == mini:
                typecodec = 'default'
            else:
                typecodec = 'mixed'
        return {'lencodec': xlen, 'mincodec': mini, 'maxcodec': maxi,
                'typecodec': typecodec, 'ratecodec': rate}

    @property
    def keys(self):
        '''return keys  '''
        return self._keys

    @property
    def typevalue(self):
        '''return typevalue calculated from name'''
        return util.typename(self.name)

    @property
    def values(self):
        '''return values (see data model)'''
        return [self._codec[key] for key in self._keys]

    @property
    def val(self):
        '''return values conversion to string '''
        return self.to_obj(modecodec='full', codecval=True, encoded=False)
