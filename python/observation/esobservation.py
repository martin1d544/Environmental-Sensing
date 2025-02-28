# -*- coding: utf-8 -*-
"""
Created on Tue Aug  3 23:40:06 2021

@author: philippe@loco-labs.io

An `Observation` is an object representing a set of information having
spatial and temporal characteristics associated with measurable or observable
 properties.

The `Observation` Object is built around three main bricks :

- Ilist Object which deal with indexing,
- ESValue Object which integrate the specificities of environmental data,
- Tools dedicated to particular domains
([Shapely](https://shapely.readthedocs.io/en/stable/manual.html)
for location, TimeSlot for Datation)

The `observation.esobservation` module contains the `Observation` class.

Documentation is available in other pages :

- The concept of 'observation' is describe in
[this page](https://github.com/loco-philippe/Environmental-Sensing/wiki/Observation).
- The concept of 'indexed list' is describe in
[this page](https://github.com/loco-philippe/Environmental-Sensing/wiki/Indexed-list).
- The non-regression test are at [this page]
(https://github.com/loco-philippe/Environmental-Sensing/blob/main/python/Tests/test_obs.py)
- The [examples]
(https://github.com/loco-philippe/Environmental-Sensing/tree/main/python/Examples/Observation)
"""
import datetime
import json
from copy import copy
import folium
import cbor2

from ilist import Ilist
from util import util
from iindex_interface import IindexEncoder, CborDecoder
from esconstante import ES
from esvalue import LocationValue, DatationValue, PropertyValue, ExternValue
from esvalue_base import ESValue, ESValueEncoder
from ilist_analysis import Analysis


class Observation(Ilist):
    """
    An `Observation` is derived from `observation.Ilist` object.

    *Additional attributes (for @property see methods)* :

    - **name** : textual description
    - **param** : namedValue dictionnary (external data)

    The methods defined in this class (included inherited) are :

    *constructor (@classmethod))*

    - `Observation.dic`
    - `Observation.std`
    - `observation.ilist.Ilist.obj`
    - `Observation.from_obj`
    - `observation.ilist.Ilist.from_file`

    *dynamic value (getters @property)*

    - `Observation.bounds`
    - `Observation.id`
    - `Observation.jsonFeature`
    - `Observation.setLocation`
    - `Observation.setDatation`
    - `Observation.setProperty`
    - `Observation.setResult`

    *dynamic value inherited (getters @property)*

    - `observation.ilist.Ilist.extidx`
    - `observation.ilist.Ilist.extidxext`
    - `observation.ilist.Ilist.idxname`
    - `observation.ilist.Ilist.idxlen`
    - `observation.ilist.Ilist.iidx`
    - `observation.ilist.Ilist.keys`
    - `observation.ilist.Ilist.lenindex`
    - `observation.ilist.Ilist.lenidx`
    - `observation.ilist.Ilist.lidx`
    - `observation.ilist.Ilist.lidxrow`
    - `observation.ilist.Ilist.lvar`
    - `observation.ilist.Ilist.lvarrow`
    - `observation.ilist.Ilist.lname`
    - `observation.ilist.Ilist.lunicname`
    - `observation.ilist.Ilist.lunicrow`
    - `observation.ilist.Ilist.setidx`

    *global value (getters @property)*

    - `observation.ilist.Ilist.complete`
    - `observation.ilist.Ilist.consistent`
    - `observation.ilist.Ilist.dimension`
    - `observation.ilist.Ilist.lencomplete`
    - `observation.ilist.Ilist.primary`
    - `observation.ilist.Ilist.zip`

    *selecting - infos methods*

    - `observation.ilist.Ilist.couplingmatrix`
    - `observation.ilist.Ilist.idxrecord`
    - `observation.ilist.Ilist.indexinfos`
    - `observation.ilist.Ilist.indicator`
    - `observation.ilist.Ilist.iscanonorder`
    - `observation.ilist.Ilist.isinrecord`
    - `observation.ilist.Ilist.keytoval`
    - `observation.ilist.Ilist.loc`
    - `observation.ilist.Ilist.nindex`
    - `observation.ilist.Ilist.record`
    - `observation.ilist.Ilist.recidx`
    - `observation.ilist.Ilist.recvar`
    - `observation.ilist.Ilist.valtokey`

    *add - update methods*

    - `observation.ilist.Ilist.add`
    - `observation.ilist.Ilist.addindex`
    - `observation.ilist.Ilist.append`
    - `Observation.appendObs`
    - `observation.ilist.Ilist.delindex`
    - `observation.ilist.Ilist.delrecord`
    - `observation.ilist.Ilist.renameindex`
    - `observation.ilist.Ilist.setname`
    - `observation.ilist.Ilist.updateindex`

    *structure management - methods*

    - `observation.ilist.Ilist.applyfilter`
    - `observation.ilist.Ilist.coupling`
    - `observation.ilist.Ilist.full`
    - `observation.ilist.Ilist.getduplicates`
    - `observation.ilist.Ilist.merge`
    - `observation.ilist.Ilist.reindex`
    - `observation.ilist.Ilist.reorder`
    - `observation.ilist.Ilist.setfilter`
    - `observation.ilist.Ilist.sort`
    - `observation.ilist.Ilist.swapindex`
    - `observation.ilist.Ilist.setcanonorder`
    - `observation.ilist.Ilist.tostdcodec`

    *exports methods*

    - `Observation.choropleth`
    - `observation.ilist.Ilist.json`
    - `observation.ilist.Ilist.plot`
    - `observation.ilist.Ilist.to_csv`
    - `observation.ilist.Ilist.to_file`
    - `Observation.to_obj`
    - `Observation.to_xarray`
    - `observation.ilist.Ilist.to_dataframe`
    - `observation.ilist.Ilist.view`
    - `observation.ilist.Ilist.vlist`
    - `observation.ilist.Ilist.voxel`
    """

# %% constructor
    def __init__(self, listidx=None, name=None, param=None, reindex=True):
        '''Observation constructor

        *Parameters*

        - **listidx**  : object (default None) - list of Iindex data or Ilist or Observation
        - **name**     : string (default None) - Obs name
        - **param**    : dict (default None) - Dict with parameter data or user's data'''

        if isinstance(listidx, Observation):
            self.lindex = [copy(idx) for idx in listidx.lindex]
            if not listidx.param is None:
                self.param = dict(listidx.param.items())
            else:
                self.param = param
            self.name = listidx.name
            self.analysis = Analysis(self)
            return

        if isinstance(listidx, Ilist):
            self.lindex = [copy(idx) for idx in listidx.lindex]
            self.param = param
            self.name = name
            self.analysis = Analysis(self)
            return

        if not listidx:
            Ilist.__init__(self)
        else:
            Ilist.__init__(self, listidx=listidx, reindex=reindex)
        self.name = name
        self.param = param
        return

    @classmethod
    def dic(cls, idxdic=None, typevalue=ES.def_clsName, name=None, param=None):
        '''
        Observation constructor (external dictionnary).

        *Parameters*

        - **idxdic** : dict (default None) - dict of Iindex element (Iindex name :
        list of Iindex values)
        - **typevalue** : str (default ES.def_clsName) - default value class (None or NamedValue)
        - **var** :  int (default None) - row of the variable
        - **name**     : string (default None) - Observation name
        - **param**    : dict (default None) - Dict with parameter data or user's data'''
        listidx = Ilist.dic(idxdic, typevalue=typevalue)
        return cls(listidx=listidx, name=name, param=param)

    @classmethod
    def std(cls, result=None, datation=None, location=None, property=None,
            name=None, param=None, typevalue=ES.def_clsName):
        '''
        Generate an Observation Object with standard indexes

        *Parameters*

        - **datation** : compatible Iindex (default None) - index for DatationValue
        - **location** : compatible Iindex (default None) - index for LocationValue
        - **property** : compatible Iindex (default None) - index for PropertyValue
        - **result  ** : compatible Iindex (default None) - index for Variable(NamedValue)
        - **name**     : string (default None) - Observation name
        - **param**    : dict (default None) - Dict with parameter data or user's data'''
        idxdic = {}
        length = 0
        std_val = (result, datation, location, property)
        es_val = (ES.res_classES, ES.dat_classES,
                  ES.loc_classES, ES.prp_classES)
        for std, esv in zip(std_val, es_val):
            value = []
            if not std is None and isinstance(std, list):
                value = std
            elif not std is None and not isinstance(std, list):
                value = [std]
            length = max(length, len(value))
            idxdic[esv] = value
        for item in idxdic.items():
            if len(item[1]) == 1:
                idxdic[item[0]] = item[1] * length
        return cls.dic(idxdic=idxdic, typevalue=typevalue, name=name, param=param)

    @classmethod
    def from_obj(cls, bs=None, reindex=True, context=True):
        '''
        Generate an Observation Object from a bytes, string or dic value

        *Parameters*

        - **bs** : bytes, string or dict data to convert
        - **reindex** : boolean (default True) - if True, default codec for each Iindex
        - **context** : boolean (default True) - if False, only codec and keys are included'''
        if not bs:
            bs = {}
        if isinstance(bs, bytes):
            dic = cbor2.loads(bs)
        elif isinstance(bs, str):
            dic = json.loads(bs, object_hook=CborDecoder().codecbor)
        elif isinstance(bs, dict):
            dic = bs
        else:
            raise ObsError("the type of parameter is not available")

        param = None
        if ES.param in dic:
            param = dic[ES.param]
        if param and not isinstance(param, dict):
            raise ObsError('param is not a dict')

        name = None
        if ES.name in dic:
            name = dic[ES.name]
        if name and not isinstance(name, str):
            raise ObsError('name is not a str')

        data = None
        if ES.data in dic:
            data = dic[ES.data]
        if data and not isinstance(data, (list, dict)):
            raise ObsError('data is not a list and not a dict')

        return cls(listidx=Ilist.obj(data, reindex=reindex, context=context),
                   name=name, param=param)

# %% special
    def __copy__(self):
        ''' Copy all the data '''
        return Observation(self)

    def __str__(self):
        '''return string format'''
        stro = ''
        if self.name:
            stro = ES.name + ': ' + self.name + '\n'
        stri = Ilist.__str__(self)
        if not stri == '':
            stro += ES.data + ':\n' + stri
        if self.param:
            stro += ES.param + ':\n    ' + json.dumps(self.param) + '\n'
        return stro

    def __hash__(self):
        '''return sum of all hash(Iindex)'''
        return hash(json.dumps(self.param)) + hash(self.name) + Ilist.__hash__(self)

# %% properties
    @property
    def bounds(self):
        '''
        **list of `observation.esvalue` (@property)** : `observation.esvalue`
        bounding box for each axis.'''
        bound = [None, None, None]
        if self.setDatation:
            bound[0] = ESValue.boundingBox(self.setDatation).bounds
        if self.setLocation:
            bound[1] = ESValue.boundingBox(self.setLocation).bounds
        if self.setProperty:
            bound[2] = ESValue.boundingBox(self.setProperty).bounds
        return bound

    @property
    def __geo_interface__(self):
        '''**dict (@property)** : return the union of Location geometry (see shapely)'''
        codecgeo = self.nindex('location').codec
        if len(codecgeo) == 0:
            return ""
        if len(codecgeo) == 1:
            return codecgeo[0].value.__geo_interface__
        collec = codecgeo[0].value
        for loc in codecgeo[1:]:
            collec = collec.union(loc.value)
        return collec.__geo_interface__

    @property
    def id(self):
        '''**integer (@property)** : hash value (unique)'''
        return hash(self)

    @property
    def jsonFeature(self):
        '''**string (@property)** : "FeatureCollection" with Location geometry'''
        if self.setLocation:
            geo = self.__geo_interface__
            if geo['type'][:5] == 'Multi':
                typ = geo['type'][5:]
                lis = [{"type":  typ, "coordinates": geo['coordinates'][i]}
                       for i in range(len(geo['coordinates']))]
            elif geo['type'] in ['Point', 'Polygon']:
                lis = [geo]
            elif geo['type'] == 'GeometryCollection':
                lis = geo['geometries']
            fea = [{"type": "Feature", "id": i, "geometry": lis[i]}
                   for i in range(len(lis))]
            return json.dumps({"type": "FeatureCollection", "features": fea},
                              cls=ESValueEncoder)
        return ''

    @property
    def setDatation(self):
        '''**list (@property)** : list of codec values in the datation index'''
        if self.nindex(ES.dat_classES):
            return self.nindex(ES.dat_classES).codec
        return None

    @property
    def setLocation(self):
        '''**list (@property)** : list of codec values in the location index'''
        if self.nindex(ES.loc_classES):
            return self.nindex(ES.loc_classES).codec
        return None

    @property
    def setProperty(self):
        '''**list (@property)** : list of codec values in the property index'''
        if self.nindex(ES.prp_classES):
            return self.nindex(ES.prp_classES).codec
        return None

    @property
    def setResult(self):
        '''
        **list (@property)** : list of codec values in the result index'''
        if self.nindex(ES.res_classES):
            return self.nindex(ES.res_classES).codec
        return None

# %% methods
    def appendObs(self, obs, unique=False, fillvalue='-'):
        '''
        Add an `Observation` as a new Result `observation.esvalue` with bounding
        box for the Index `observation.esvalue`

        *Parameters*

        - **obs** : Observation object
        - **fillvalue** : object value used for default value

        *Returns*

        - **int** : last index in the `Observation`'''
        lname = self.lname
        record = [fillvalue] * len(lname)
        if ES.dat_classES in lname:
            record[lname.index(ES.dat_classES)] = DatationValue.Box(
                obs.bounds[0])
        if ES.loc_classES in lname:
            record[lname.index(ES.loc_classES)] = LocationValue.Box(
                obs.bounds[1])
        if ES.prp_classES in lname:
            record[lname.index(ES.prp_classES)] = PropertyValue.Box(
                obs.bounds[2])
        if ES.res_classES in lname:
            record[lname.index(ES.res_classES)] = ExternValue(obs)
        return self.append(record, unique=unique)

    def choropleth(self, name="choropleth", line=True):
        '''
        Display `Observation` on a folium.Map (only with dimension=1)

        - **name** : String, optionnal (default 'choropleth') - Name of the choropleth
        - **line** : Boolean, optionnal (default True) - Line between recods if True

        *Returns* : None'''
        primary = self.primary
        if self.dimension == 1:
            mapf = folium.Map(
                location=self.setLocation[0].coorInv, zoom_start=6)
            folium.Choropleth(
                geo_data=self.jsonFeature,
                name=self.name,
                data=self.to_xarray(
                    numeric=True, coord=True).to_dataframe(name='obs'),
                key_on="feature.id",
                columns=[self.idxname[primary[0]] + '_row', 'obs'],
                fill_color="OrRd",
                fill_opacity=0.7,
                line_opacity=0.4,
                line_weight=2,
                legend_name=name
            ).add_to(mapf)
            if line:
                folium.PolyLine(
                    util.funclist(self.nindex('location'),
                                  LocationValue.vPointInv)
                ).add_to(mapf)
            folium.LayerControl().add_to(mapf)
            return mapf
        return None

    def to_obj(self, **kwargs):
        '''Return a formatted object (json string, cbor bytes or json dict).

        *Parameters (kwargs)*

        - **encoded** : boolean (default False) - choice for return format
        (string/bytes if True, dict else)
        - **encode_format**  : string (default 'json')- choice for return format (json, cbor)
        - **codif** : dict (default ES.codeb). Numerical value for string in CBOR encoder
        - **modecodec** : string (default 'optimize') - if 'full', each index is with a full codec
        if 'default' each index has keys, if 'optimize' keys are optimized,
        if 'dict' dict format is used, if 'nokeys' keys are absent, if 'ndjson' 
        a list of ndjson elements is created
        - **name** : boolean (default False) - if False, default index name are not included
        - **fullvar** : boolean (default True) - if True and modecodec='optimize,
        variable index is with a full codec
        - **geojson** : boolean (default False) - geojson for LocationValue if True

        - **json_param**     : Boolean - include Obs Param
        - **json_info**      : Boolean - include all infos
        - **json_info_detail**: Boolean - include the other infos

        *Returns* : string, bytes or dict'''
        option = {'modecodec': 'optimize', 'encoded': False,
                  'encode_format': 'json', 'codif': ES.codeb, 'name': False,
                  'json_param': False, 'json_info': False, 'json_info_detail': False,
                  'geojson': False, 'fullvar': True} | kwargs
        if option['modecodec'] == 'ndjson':
            lisobs = {ES.id: self.id}
            if self.param:
                lisobs[ES.param] = self.param
            if self.name:
                lisobs[ES.name] = self.name
            return [lisobs] + Ilist.to_obj(self, modecodec='ndjson', id=self.id)
        option2 = option | {'encoded': False, 'encode_format': 'json'}
        dic = {ES.type: ES.obs_classES}

        if self.name:
            dic[ES.obs_name] = self.name
        if self.param:
            dic[ES.obs_param] = self.param
        dic[ES.obs_data] = Ilist.to_obj(self, **option2)
        if option["json_param"] and self.param:
            dic[ES.obs_param] = self.param
        dic |= self._info(**option)
        if option['codif'] and option['encode_format'] != 'cbor':
            js2 = {}
            for key, val in dic.items():
                if key in option['codif']:
                    js2[option['codif'][key]] = val
                else:
                    js2[key] = val
        else:
            js2 = dic

        if option['encoded'] and option['encode_format'] == 'json':
            return json.dumps(js2, cls=IindexEncoder)
        if option['encoded'] and option['encode_format'] == 'cbor':
            return cbor2.dumps(js2, datetime_as_timestamp=True,
                               timezone=datetime.timezone.utc, canonical=True)
        return dic

    def to_xarray(self, info=False, idxname=None, varname=None, fillvalue='?',
                  fillextern=True, lisfunc=None, numeric=False, npdtype=None,
                  **kwargs):
        '''
        Complete the Observation and generate a Xarray DataArray with the dimension define by idx.

        *Parameters*

        - **info** : boolean (default False) - if True, add _dict attributes to attrs Xarray
        - **idxname** : list (default none) - list of idx to be completed. If None,
        self.primary is used.
        - **varname** : string (default none) - Name of the variable to use. If None,
        first lvarname is used.
        - **fillvalue** : object (default '?') - value used for the new extval
        - **fillextern** : boolean(default True) - if True, fillvalue is converted to typevalue
        - **lisfunc** : function (default none) - list of function to apply to indexes before export
        - **numeric** : Boolean (default False) - Generate a numeric DataArray.Values.
        - **npdtype** : string (default None) - numpy dtype for the DataArray ('object' if None)
        - **kwargs** : parameter for lisfunc

        *Returns* : DataArray '''
        return Ilist.to_xarray(self, info=info, idxname=idxname, varname=varname,
                               fillvalue=fillvalue, fillextern=fillextern,
                               lisfunc=lisfunc, name=self.name, numeric=numeric,
                               npdtype=npdtype, attrs=self.param, **kwargs)
# %% internal

    def _info(self, **kwargs):
        ''' Create json dict with info datas

        *Parameters*

        - **json_info** : boolean (default False) - if True, add main information
        about Observation and Iindex
        - **json_info_detail** : boolean (default False) - if True, add complemantary
        information about Iindex
        '''
        option = {"json_info": False, "json_info_detail": False} | kwargs
        dcobs = {}
        dcindex = {}
        if not option['json_info']:
            return dcobs
        dcobs[ES.name] = self.name
        dcobs[ES.id] = self.id
        dcobs[ES.length] = len(self)
        dcobs[ES.lenindex] = self.lenindex
        dcobs[ES.complete] = self.complete
        dcobs[ES.dimension] = self.dimension
        if option['json_info_detail']:
            infos = self.indexinfos()
        for ind, idx in enumerate(self.lidx):
            dcidx = {}
            dcidx[ES.num] = ind
            dcidx[ES.typevalue] = idx.typevalue
            dcidx[ES.lencodec] = len(idx.codec)
            dcidx[ES.box] = Observation._info_box(idx, **option)
            if option['json_info_detail']:
                dcidx |= infos[ind]
            dcindex[idx.name] = dcidx
        return {ES.information: {ES.observation: dcobs, ES.index: dcindex}}

    @staticmethod
    def _info_box(idx, **option):
        ''' return box informations's'''
        if idx.typevalue == ES.dat_clsName:
            return DatationValue.boundingBox(idx.codec)
        if idx.typevalue == ES.loc_clsName and not option["geojson"]:
            return LocationValue.boundingBox(idx.codec)
        if idx.typevalue == ES.loc_clsName and option["geojson"]:
            return LocationValue.Box(LocationValue.boundingBox(idx.codec)).__geo_interface__
        if idx.typevalue == ES.prp_clsName:
            return PropertyValue.boundingBox(idx.codec)
        return None


class ObsError(Exception):
    '''Observation exception'''
