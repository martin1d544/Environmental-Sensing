'''
# How to use observation.essearch ?

1. **Create the MongoDB database:**
You can easily create an account on MongoDB. Once you have a database, follow the guidelines [here](https://www.mongodb.com/docs/atlas/tutorial/connect-to-your-cluster/#connect-to-your-atlas-cluster) to connect to it using pymongo.
All you need in order to be able to use this module is to be able to connect to the Collection with pymongo.

2. **Fill the database with your data:**
Construct an observation or a list of observations containing your data using dedicated functions from `observation.Observation`. 
You can then use `insert_mongo(collection, observation)` to insert it in the database.

3. **Write a request using observation.ESSearch:**
An `ESSearch` instance must be created with either a MongoDB Collection (passed as argument **collection**) or a list of observations (passed as argument **data**).
Criteria for the query are then added one by one using `ESSearch.addCondition` or `ESSearch.orCondition`, or all together with `ESSearch.addConditions` or passed as argument **parameters** of ESSearch.

A condition is composed of:
- a **path** giving which element is concerned by the condition;
- an **operand** which is the item of the comparison (if omitted, the existence of the path is tested);
- a **comparator** which can be applied on the operand, for example '>=' or 'within' (defaults to equality in most cases);
- optional parameters detailed in `ESSearch.addCondition` documentation, like **inverted** to add a *not*.

Execute the research with `ESSearch.execute()`. Put the parameter **single** to True if you want the return to be a single observation
instead of a list of observations.

Example of python code using observation.essearch module:
```python
from pymongo import MongoClient
from observation.essearch import ESSearch
import datetime

client = Mongoclient(<Mongo-auth>)
collection = client[<base>][<collection>]

# In this example, we search for measures of property PM25 taken between 2022/01/01 
# and 2022/31/12 and we ensure the measure is an Observation.
# We execute with argument single = True to merge the result in one single
# Observation.

# Option 1
srch = ESSearch(collection)
srch.addCondition('datation', datetime.datetime(2022, 1, 1), '>=')
srch.addCondition('datation', datetime.datetime(2022, 12, 31), '<=')
srch.addCondition('property', 'PM25')
srch.addCondition(path = 'type', comparator = '==', operand = 'observation')
result = srch.execute(single = True)

# Option 2 (equivalent to option 1 but on one line)
result = ESSearch(collection,
                [['datation', datetime.datetime(2022, 1, 1), '>='], 
                ['datation', datetime.datetime(2022, 12, 31), '<='], 
                ['property', 'PM25'], 
                {'path': 'type', 'comparator': '==', 'operand': 'observation'}] 
                ).execute(single = True)
```
'''
import datetime
import shapely.geometry
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.command_cursor import CommandCursor
from esobservation import Observation
from iindex import Iindex
from util import util
from timeslot import TimeSlot
import bson

dico_alias_mongo = { # dictionnary of the different names accepted for each comparator and each given type. <key>:<value> -> <accepted name>:<name in MongoDB>
    # any type other than those used as keys is considered non valid
    str : {
        None:"$eq",
        "eq":"$eq", "=":"$eq", "==":"$eq", "$eq":"$eq",
        "in":"$in", "$in":"$in",
        "regex":"$regex", "$regex":"$regex",
        "oid":"$oid","$oid":"$oid"
    },
    int : {
        None:"$eq",
        "eq":"$eq", "=":"$eq", "==":"$eq", "$eq":"$eq",
        "gte":"$gte", ">=":"$gte", "=>":"$gte", "$gte":"$gte",
        "gt":"$gt", ">":"$gt", "$gt":"$gt",
        "lte":"$lte", "<=":"$lte", "=<":"$lte", "$lte":"$lte",
        "lt":"$lt", "<":"$lt", "$lt":"$lt",
        "in":"$in", "$in":"$in"
    },
    datetime.datetime : {
        None:"$eq",
        "eq":"$eq", "=":"$eq", "==":"$eq", "$eq":"$eq",
        "gte":"$gte", ">=":"$gte", "=>":"$gte", "$gte":"$gte",
        "gt":"$gt", ">":"$gt", "$gt":"$gt",
        "lte":"$lte", "<=":"$lte", "=<":"$lte", "$lte":"$lte",
        "lt":"$lt", "<":"$lt", "$lt":"$lt",
        "in":"$in", "$in":"$in"
    },
    TimeSlot : {
        None:"within",
        "eq":"within", "=":"within", "==":"within", "$eq":"within", "within":"within", "within":"within",
        "contains":"intersects", "$contains":"intersects",
        "in":"within", "$in":"within", "within":"within", "$within":"within",
        "disjoint":"disjoint", "$disjoint":"disjoint",
        "intersects":"intersects", "$intersects":"intersects"
    },
    list : { # lists are interpreted as geometries
        None:"$geoIntersects",
        "eq":"equals", "=":"equals", "==":"equals", "$eq":"equals", "equals":"equals", "$equals":"equals",
        "$geowithin":"$geoWithin", "geowithin":"$geoWithin", "$geoWithin":"$geoWithin", "geoWithin":"$geoWithin", "within":"$geoWithin", "$within":"$geoWithin",
        "disjoint":"disjoint", "$disjoint":"disjoint",
        "intersects":"$geoIntersects", "$intersects":"$geoIntersects", "geoIntersects":"$geoIntersects", "$geointersects":"$geoIntersects", "geoIntersects":"$geoIntersects", "$geoIntersects":"$geoIntersects",
        "touches":"touches", "$touches":"touches",
        "overlaps":"overlaps", "$overlaps":"overlaps",
        "contains":"contains", "$contains":"contains",
        "$geoNear":"$geoNear", "$geonear":"$geoNear", "geonear":"$geoNear", "geoNear":"$geoNear",
        
        "in":"$in", "$in":"$in" # only in case where a list is not a geometry
    },
    bson.objectid.ObjectId : {
        None:"$eq",
        "eq":"$eq", "=":"$eq", "==":"$eq", "$eq":"$eq",
        "in":"$in", "$in":"$in"
    }
}
dico_alias_mongo[float] = dico_alias_mongo[int]

_geoeq    = lambda x, y: x.equals(y)
_geowith  = lambda x, y: x.within(y)
_geodis   = lambda x, y: x.disjoint(y)
_geointer = lambda x, y: x.intersects(y)
_geotou   = lambda x, y: x.touches(y)
_geoover  = lambda x, y: x.overlaps(y)
_geocont  = lambda x, y: x.contains(y)
_geonear  = lambda x, y: True

_defeq    = lambda x, y: x == y
_defsupeq = lambda x, y: x >= y
_defsup   = lambda x, y: x > y
_definfeq = lambda x, y: x <= y
_definf   = lambda x, y: x < y
_defin    = lambda x, y: x in y

_timinfeq = lambda x, y: x.bounds[0] <= y # at least one element of the TimeSlot is lte y
_timinf   = lambda x, y: x.bounds[0] < y  # at least one element of the TimeSlot is lt y
_timsupeq = lambda x, y: x.bounds[1] >= y # at least one element of the TimeSlot is gte y
_timsup   = lambda x, y: x.bounds[1] > y  # at least one element of the TimeSlot is gt y
_timeq    = lambda x, y: x == TimeSlot(y)
# To have all elements verify a comparison instead of just one, combine with parameter inverted.
# For example : not (at least one element of the TimeSlot is lte y) <=> all elements of the TimeSlot are gt y

dico_alias_python = {
    TimeSlot : { # only used in python filtering part
        TimeSlot : { # comparison of a TimeSlot with a timeSlot
            None:"equals",
            "eq":"equals", "=":"equals", "==":"equals", "$eq":"equals", "equals":"equals", "$equals":"equals",
            "contains":"contains", "$contains":"contains",
            "in":"within", "$in":"within", "within":"within", "$within":"within",
            "disjoint":"disjoint", "$disjoint":"disjoint",
            "intersects":"intersects", "$intersects":"intersects"
        },
            
        datetime.datetime : { # comparison of a datetime and a TimeSlot
            None:_timeq,
            "eq":_timeq, "=":_timeq, "==":_timeq, "$eq":_timeq, "equals":_timeq, "$equals":_timeq,
            "$gte":_timsupeq, "gte":_timsupeq, ">=":_timsupeq, "=>":_timsupeq,
            "$gt":_timsup, "gt":_timsup, ">":_timsup,
            "$lte":_timinfeq, "lte":_timinfeq, "<=":_timinfeq, "=<":_timinfeq,
            "$lt":_timinf, "lt":_timinf, "<":_timinf
        }
    },
    'geometry' : { # lists are interpreted as geometries
        None:_geointer,
        "eq":_geoeq, "=":_geoeq, "==":_geoeq, "$eq":_geoeq, "equals":_geoeq, "$equals":_geoeq,
        "$geowithin":_geowith, "geowithin":_geowith, "$geoWithin":_geowith, "geoWithin":_geowith, "within":_geowith, "$within":_geowith,
        "disjoint":_geodis, "$disjoint":_geodis,
        "intersects":_geointer, "$intersects":_geointer, "geoIntersects":_geointer, "$geointersects":_geointer, "geoIntersects":_geointer, "$geoIntersects":_geointer,
        "touches":_geotou, "$touches":_geotou,
        "overlaps":_geoover, "$overlaps":_geoover,
        "contains":_geocont, "$contains":_geocont,
        "$geoNear":_geonear, "$geonear":_geonear, "geonear":_geonear, "geoNear":_geonear
    },
    'default' : {
        None:_defeq,
        "eq":_defeq, "=":_defeq, "==":_defeq, "$eq":_defeq,
        "gte":_defsupeq, ">=":_defsupeq, "=>":_defsupeq, "$gte":_defsupeq,
        "gt":_defsup, ">":_defsup, "$gt":_defsup,
        "lte":_definfeq, "<=":"$lte", "=<":_definfeq,
        "lt":_definf, "<":_definf, "$lt":_definf,
        "in":_defin, "$in":_defin
    }
}

def insert_from_doc(collection, document , info=True):
    '''Inserts all observations from a document into a collection, where each line of the document corresponds to an observation.'''
    with open(document, 'r') as doc:
        for line in doc:
            try: insert_to_mongo(collection, line, info)
            except: pass

def insert_to_mongo(collection, obj, info=False): # Mieux avec panda ?
    '''Takes an observation or a list of observations and inserts them into a MongoDB collection, with info by default.'''
    # Faire une fonction pour permettre l'ajout direct de fichiers csv.
    inserted_list = []
    if isinstance(obj, list):
        pile = obj
    elif isinstance(obj, Observation):
        pile = [obj]
    else:
        pile = [Observation.from_obj(obj)]
    for obs in pile:
        if obs.id: obs_hash = obs.id
        else: obs_hash = hash(obs)
        metadata = {'id': obs_hash}
        if obs.name : metadata['name']  = obs.name
        if obs.param: metadata['param'] = obs.param
        if info: metadata['information'] = Observation._info(True, True)
        if len(obs.lname) == 1: # a special case is needed because lists with one element are replaced by the element itself so iteration doesn't work
            for line in obs:
                inserted_list.append({obs.lname[0]: util.json(line, encoded=False, typevalue=None, simpleval=False, geojson=True),
                                        '_metadata': metadata})
        elif len(obs.lname) > 1:
            for line in obs:
                inserted_list.append({obs.lname[i]: util.json(line[i], encoded=False, typevalue=None, simpleval=False, geojson=True) 
                                                                for i in range(len(line))} | {'_metadata': metadata})
    if inserted_list != []: collection.insert_many(inserted_list)

def empty_request(collection):
    """
    Empty request to get an idea of what the database contains.
    Currently returns the count of elements in the collection and the name of each column.
    """
    count = 0
    column_names = []
    cursor = collection.find()
    for doc in cursor:
        count += 1
        for column_name in doc:
            if column_name not in column_names:
                column_names.append(column_name)
    return {'count': count, 'column_names': column_names}

class ESSearch:
    """
    An `ESSearch` is defined as an ensemble of conditions to be used to execute a MongoDB request or any iterable containing only observations.

    *Attributes (for @property, see methods)* :

    - **input** : input on which the query is done. One of or a list of these : 
        - pymongo.collection.Collection
        - pymongo.cursor.Cursor
        - pymongo.command_cursor.CommandCursor
        - Observation (can be defined from a str or a dict)
    - **parameters** : list of list of conditions for queries, to be interpreted as : parameters = [[cond_1 AND cond_2 AND cond_3] OR [cond_4 AND cond_5 AND cond_6]] where conds are criteria for queries
    - **hide** : list of paths to hide from the output
    - **heavy** : boolean indicating whether the request should search for nested values or not. Does not work with geoJSON.
    - **sources** : attribute used to indicate the sources of the data in param

    The methods defined in this class are (documentations in methods definitions):
    
    *setter*

    - `ESSearch.addInput`
    - `ESSearch.removeInputs`
    - `ESSearch.setHide`
    - `ESSearch.setHeavy`
    - `ESSearch.clear`
    
    *dynamic value (getter @property)*

    - `ESSearch.request`
    - `ESSearch.cursor`
    
    *parameters for query - update methods*

    - `ESSearch.addConditions`
    - `ESSearch.addCondition`
    - `ESSearch.orCondition`
    - `ESSearch.removeCondition`
    - `ESSearch.clearConditions`

    *query method*

    - `ESSearch.execute`
    """
    def __init__(self,
                    input = None,
                    parameters = None,
                    hide = [],
                    heavy = False,
                    sources = None, 
                    **kwargs
                    ):
        '''
        ESSearch constructor. Parameters can also be defined and updated using class methods.

        *Arguments*

        - **input** : input on which the query is done. Must be one of or a list of these (can be nested):
            - pymongo.collection.Collection
            - pymongo.cursor.Cursor
            - pymongo.command_cursor.CommandCursor
            - Observation
            - str corresponding to a json Observation
            - dict corresponding to a json Observation
        - **parameters** :  dict, list (default None) - list of list or list of dictionnaries whose keys are arguments of ESSearch.addCondition method
        ex: parameters = [
            {'name' : 'datation', 'operand' : datetime.datetime(2022, 9, 19, 1), 'comparator' : '>='},
            {'name' : 'property', 'operand' : 'PM2'}
        ]
        - **hide** : list (default []) - List of strings where strings correspond to paths to remove from the output
        - **heavy** :  bool (default False) - Must be True when values are defined directly and inside dictionnaries simultaneously.
        - **sources** : (default None) - Optional parameter indicating the sources of the data in case when a query is executed with parameter single = True.
        - **kwargs** :  other parameters are used as arguments for ESSearch.addCondition method.
        '''
        self.parameters = [[]]                                          # self.parameters
        if isinstance(hide, list): self.hide = hide                     # self.hide
        else: raise TypeError("hide must be a list.")

        if isinstance(heavy, bool): self.heavy = heavy                  # self.heavy
        else: raise TypeError("heavy must be a bool.")
        self.sources = sources                                          # self.sources

        self.input = [[], []]                                           # self.input : formatted as [[Mongo Objects], [Observations]] (list of two lists)
        if isinstance(input, list): pile = input
        else: pile = [input]
        while not len(pile) == 0:
            obj = pile.pop()
            if isinstance(obj, list):
                pile += obj
            elif isinstance(obj, (Collection, Cursor, CommandCursor)):
                self.input[0].append(obj)
            elif isinstance(obj,  Observation):
                self.input[1].append(obj)
            elif isinstance(obj, (str, dict)):
                try:
                    self.input[1].append(Observation.from_obj(obj))
                except:
                    raise ValueError("Cannot convert " + str(obj) + " to an Observation.")
            elif obj is not None:
                raise TypeError("Unsupported type for input " + str(obj))

        if parameters: self.addConditions(parameters)
        if kwargs: self.addCondition(**kwargs)

    def __repr__(self):
        return "ESSearch(input = " + str(self.input) + ", parameters = " + str(self.parameters) + ")"

    def __str__(self):
        return str(self.parameters)

    def __iter__(self):
        self.n = -1
        return self

    def __next__(self):
        if self.n < len(self.parameters)-1:
            self.n += 1
            return self.parameters[self.n]
        else:
            raise StopIteration

    def __getitem__(self, key):
        return self.parameters[key]

    def addInput(self, input):
        """
        Adds one or many inputs on which the query is to be executed given by argument input.
        Inputs can be:
            - pymongo.collection.Collection
            - pymongo.cursor.Cursor
            - pymongo.command_cursor.CommandCursor
            - Observation
            - str corresponding to a json Observation
            - dict corresponding to a json Observation
        or a list of any of these.
        """
        added_input = [[], []]
        if isinstance(input, list): pile = input
        else: pile = [input]
        while not len(pile) == 0: # using a stack (LIFO) to allow easy treatment of nested data.
            obj = pile.pop()
            if isinstance(obj, list):
                pile += obj
            elif isinstance(obj, (Collection, Cursor, CommandCursor)):
                added_input[0].append(obj)
            elif isinstance(obj,  Observation):
                added_input[1].append(obj)
            elif isinstance(obj, (str, dict)):
                try:
                    added_input[1].append(Observation.from_obj(obj))
                except:
                    raise ValueError("Cannot convert " + str(obj) + " to an Observation.")
            elif obj is not None:
                raise TypeError("Unsupported type for input " + str(obj))
        self.input[0] += added_input[0] # self.input is updated with the new inputs
        self.input[1] += added_input[1]

    def removeInputs(self):
        """
        Removes all inputs from self.
        """
        self.input = [[], []]

    def setHide(self, hide):
        '''
        Sets self.hide to a value given by argument hide.
        '''
        if isinstance(hide, list): self.hide = hide
        else: raise TypeError("hide must be a list.")
        
    def setHeavy(self, heavy):
        '''
        Sets self.heavy to a value given by argument heavy.
        '''
        if isinstance(heavy, list): self.heavy = heavy
        else: raise TypeError("heavy must be a bool.")

    def setSources(self, sources):
        '''
        Sets self.sources to a value given by argument sources.
        '''
        self.sources = sources

    def addConditions(self, parameters):
        '''
        Takes multiple parameters and applies self.addCondition() on each of them.
        '''
        if isinstance(parameters, dict): # case when one single condition is added
            self.addCondition(**parameters)
        elif isinstance(parameters, (list, tuple)): # case when several conditions are added
            for parameter in parameters:
                if isinstance(parameter, dict): self.addCondition(**parameter)
                elif isinstance(parameters, (list, tuple)): self.addCondition(*parameter)
                else: self.addCondition(parameter)
        else: raise TypeError("parameters must be either a dict or a list of dict.")
            
    def addCondition(self, path, operand = None, comparator = None, or_position = -1, **kwargs):
        '''
        Takes parameters and inserts corresponding query condition in self.parameters.

        *Parameters*

        - **path** :  str (required argument) - name of an IIndex, which corresponds to an Ilist column name, or name of a metadata element.
                    (ex: 'datation', 'location', 'property')

        - **operand** :  - (default None) - Object used for the comparison.
                    (ex: if we search for observations made in Paris, operand is 'Paris')

        - **comparator**:  str (default None) - str giving the comparator to use. (ex: '>=', 'in')
        
        - **or_position** :  int (default -1) - position in self.parameters in which the condition is to be inserted.

        - **formatstring** :  str (default None) - str to use to automatically change str to datetime before applying condition.
                    Does not update the data base. If value is set to 'default', format is assumed to be Isoformat.
        
        - **inverted** :  bool (default None) - to add a "not" in the condition.
                    To use in case where every element of a MongoDB array (equivalent to python list) must verify the condition (by default, condition is verified when at least one element of the array verifies it).
        
        - **unwind** :  int (default None) - int corresponding to the number of additional {"$unwind" : "$" + path} to be added in the beginning of the query.
        
        - **regex_options** :  str (default None) - str associated to regex options (i, m, x and s). See [this link](https://www.mongodb.com/docs/manual/reference/operator/query/regex/) for more details.

        no comparator => default comparator associated with operand type in dico_alias_mongo is used (mainly equality)
        no operand => only the existence of something located at path is tested
        '''

        ## 1. Check if arguments given are valid.

        if not isinstance(path, str): raise TypeError("name must be a str.")
        if comparator is not None and not isinstance(comparator, str): raise TypeError("comparator must be a str.")
        if or_position is not None and not isinstance(or_position, int): raise TypeError("or_position must be an int.")

        for item in kwargs: # checking if parameters in kwarg do exist
            if item not in {'formatstring', 'inverted', 'unwind', 'regex_options', 'distanceField', 'distanceMultiplier', 'includeLocs', 'key', 'maxDistance', 'minDistance', 'near', 'query', 'spherical'}:
                raise ValueError("Unknown parameter : ", item)

        if isinstance(operand, datetime.datetime) and (operand.tzinfo is None or operand.tzinfo.utcoffset(operand) is None):
            operand = operand.replace(tzinfo=datetime.timezone.utc)

        if operand: # checking if comparator can be applied on the operand
            try: comparator = dico_alias_mongo[type(operand)][comparator]
            except: raise ValueError("Incompatible values for comparator and operand. Ensure parameters are in the correct order.")
        elif comparator:
            raise ValueError("operand must be defined when comparator is used.")
        
        ## 2. Add the condition to self.parameters

        condition = {"comparator" : comparator, "operand" : operand, "path" : path} | kwargs

        if or_position >= len(self.parameters):
            self.parameters.append([condition])
        else:
            self.parameters[or_position].append(condition)

    def orCondition(self, *args, **kwargs):
        '''
        Adds a condition in a new sublist in self.parameters. Separations in sublists correspond to "or" in the query.
        '''
        self.addCondition(or_position = len(self.parameters), *args, **kwargs)

    def removeCondition(self, or_position = None, condnum = None):
        '''
        Removes a condition from self.parameters. By default, last element added is removed.
        Otherwise, the removed condition is the one at self.parameters[or_position][condnum].

        To remove all conditions, use ESSearch.clearConditions() method.
        '''
        if self.parameters == [[]]: return
        if or_position is None:
            if condnum is None: # by default : remove the very last added condition.
                if len(self.parameters[-1]) > 1: self.parameters[-1].pop(-1)
                else: self.parameters.pop(-1)
            else:
                if len(self.parameters[-1]) > 1 or condnum > 1: self.parameters[-1].pop(condnum)
                else: self.parameters.pop(-1)
        else:
            if condnum is None or (len(self.parameters[or_position]) == 1 and condnum == 0): self.parameters.pop(or_position) # if or_position is not None and condnum is, the whole sublist at or_position is removed.
            else: self.parameters[or_position].pop(condnum)
        if self.parameters == []: # ensure self.parameters returns to its default value after being emptied
            self.parameters = [[]]

    def clearConditions(self):
        '''
        Removes all conditions from self.parameters.
        To remove all attributes, use ESSearch.clear() method.
        '''
        self.parameters = [[]]

    def clear(self):
        '''
        Resets self.
        (Creating a new Observation would be smarter than using this function.)
        '''
        self = ESSearch()

    def _cond(self, or_pos, operand, comparator, path, inverted = False, formatstring = None, unwind = None, regex_options = None, **kwargs):
        '''
        Takes parameters and adds corresponding MongoDB expression to self._match.
        self._unwind and self._set are updated when necessary.
        '''
        if unwind:
            if isinstance(unwind, str):
                self._unwind.append(unwind)
            elif isinstance(unwind, int):
                for _ in range(unwind): self._unwind.append(path)
            elif isinstance(unwind, tuple): # format : (<path>, <unwind quantity>)
                for _ in range(unwind[1]): self._unwind.append(unwind[0])
            else: raise TypeError("unwind must be a tuple, a str or an int.")

        if self.heavy and operand is not None:
            if path not in self._heavystages: self._heavystages.add(path) # peut-être mieux de laisser l'utilisateur choisir manuellement
            path = "_" + path + ".v"

        if operand is None: # no operand => we only test if there is something located at path
            comparator = "$exists"
            operand = 1
        else:
            try: comparator = dico_alias_mongo[type(operand)][comparator] #global variable
            except:
                if formatstring:
                    try: comparator = dico_alias_mongo[datetime.datetime][comparator]
                    except: raise ValueError("Comparator not allowed.")
                elif isinstance(operand, shapely.geometry.base.BaseGeometry):
                    operand = {"type" : operand.geom_type, "coordinates" : list(operand.exterior.coords)}
                else: raise ValueError("Comparator not allowed.")

        ##if path in {"$year", "$month", "$dayOfMonth", "$hour", "$minute", "$second", "$millisecond", "$dayOfYear", "$dayOfWeek"}:
        ##    self._set |= {path[1:]: {'datation' : path}} #à tester
        ##    path = datation
        ##    self._project |= {name[1:]:0}

        if isinstance(operand, TimeSlot): #equals->within, contains->intersects, within, disjoint, intersects
            self._filtered = True
            if comparator == "within":
                self._cond(or_pos, operand[0].start, "$gte", path, False)
                self._cond(or_pos, operand[-1].end, "$lte", path, False)
            elif comparator == "intersects":
                self._cond(or_pos, operand[0].start, "$lte", path, False) # pourquoi False et pas inverted ici ??
                self._cond(or_pos, operand[-1].end, "$gte", path, False)
            return

        if formatstring:
            if formatstring == "default":
                if isinstance(operand, str):
                    operand = datetime.datetime.fromisoformat(operand)
                self._set |= {path : {"$convert": {"input" : "$" + path, "to" : "date", "onError" : "$" + path}}}
            else:
                if isinstance(operand, str):
                    datetime.datetime.strptime(operand, formatstring)
                self._set |= {path : {"$dateFromString" : {"dateString" : "$" + path, "format": formatstring, "onError": "$" + path}}}

        if comparator in {"$geoIntersects", "$geoWithin"}:  # operand :
                                                            # [x, y] or [[x, y]] -> Point ;
                                                            # [[x1, y1], [x2, y2]] -> LineString ;
                                                            # [[x1, y1], [x2, y2], [x3, y3], ...] or [[x1, y1], [x2, y2], [x3, y3], ..., [x1, y1]] or [[[x1, y1], [x2, y2], [x3, y3], ..., [x1, y1]]] -> Polygon.
            if isinstance(operand, list):
                if not isinstance(operand[0], list):
                    geom_type = "Point"
                    coordinates = operand
                elif not isinstance(operand[0][0], list):
                    if len(operand) == 1:
                        geom_type = "Point"
                        coordinates = operand[0]
                    elif len(operand) == 2:
                        geom_type = "LineString"
                        coordinates = operand
                    elif len(operand) > 2:
                        if not operand[-1] == operand[0]:
                            operand.append(operand[0])
                        geom_type = "Polygon"
                        coordinates = [operand]
                    else: raise ValueError("Unable to define a geometry from " + str(operand))
                else:
                    geom_type = "Polygon"
                    coordinates = operand
                operand = {"$geometry" : {"type" : geom_type, "coordinates" : coordinates}}
            elif isinstance(operand, dict) and '$geometry' not in operand:
                operand = {"$geometry" : operand}
        elif comparator == "$geoNear": # $geoNear is a MongoDB stage
            self._geonear = self._geonear | kwargs
            if 'distanceField' not in self._geonear: raise ValueError("distanceField missing in MongoDB stage $geoNear.")
            return
        elif isinstance(operand, list): # lists are interpreted as geometries. An additional filtering is necessary for geometry-specific functions
            self._filtered = True
            return
        
        if comparator == "$regex" and regex_options:
            cond_0 = {"$regex" : operand, "$options" : regex_options}
        else:
            cond_0 = {comparator : operand}
        
        if inverted:
            if path in self._match[or_pos]:
                if "$nor" in self._match[or_pos][path]:
                    self._match[or_pos][path]["$nor"].append(cond_0)
                elif "not" in self._match[or_pos][path]:
                    self._match[or_pos][path]["$nor"] = [self._match[or_pos][path]["$not"], cond_0]
                    del self._match[or_pos][path]["$not"]
                else:
                    self._match[or_pos][path]["$not"] = cond_0
            else:
                self._match[or_pos][path] = {"$not" : cond_0}
        else:
            if path not in self._match[or_pos]:
                self._match[or_pos][path] = cond_0
            else:
                self._match[or_pos][path] |= cond_0

    def _fullSearchMongo(self):
        """
        Takes self.parameters and returns a MongoDB Aggregation query.
        """
        ## ESSearch._fullSearchMongo() 1: Declare private variables

        request = []
        self._match = []
        self._unwind = []
        self._heavystages = set() # two additional set stages to treat nested objects
        self._set = {}
        self._geonear = {}
        self._match = []
        self._project = {"_id" : 0}
        for el in self.hide: self._project |= {el : 0}
        
        ## ESSearch._fullSearchMongo() 2: Update private variables for each condition

        for i in range(len(self.parameters)): # rewriting conditions in MongoDB format
            self._match.append({})
            for cond in self.parameters[i]:
                self._cond(or_pos = i, **cond)

        ## ESSearch._fullSearchMongo() 3: Case 1 : find request

        if not self._unwind and not self.heavy and not self._set and not self._geonear: # collection.find() request
            if self._match:
                j = 0
                for i in range(len(self._match)):
                    if self._match[i] and j != i: # removing empty elements in place
                        self._match[j] = self._match[i]
                        j += 1
                if j == 0: # when there is no $or
                    if self._match[0]: match = self._match[0]
                else: # when there is a $or
                    match = {"$or": self._match[:j]}
            return 'find', match

        ## ESSearch._fullSearchMongo() 4: Case 2 : aggregate request

        else:
            if self._unwind:                                                    # Mongo $unwind stage
                for unwind in self._unwind:
                    request.append({"$unwind" : "$" + unwind})
            if self._heavystages:                                               # Additional Mongo $set stage if self.heavy is True
                heavy = {}
                for path in self._heavystages:
                    heavy |= {"_"+path:{"$cond":{"if":{"$eq":[{"$type":"$"+path},"object"]},"then":{"$objectToArray":"$"+path},"else": {"v":"$"+path}}}}
                    self._project |= {'_' + path: 0}
                request.append({"$set" : heavy})
            if self._set: request.append({"$set" : self._set})                  # Mongo $set stage
            if self._geonear: request.append({"$geoNear" : self._geonear})      # Mongo $geoNear stage
            if self._match:                                                     # Mongo $match stage
                j = 0
                for i in range(len(self._match)):
                    if self._match[i] and j != i:
                        self._match[j] = self._match[i]
                        j += 1
                if j == 0: # when there is no $or
                    if self._match[0]: request.append({"$match" : self._match[0]})
                else: # when there is a $or
                    request.append({"$match" : {"$or": self._match[:j]}})
            if self._unwind:                                                    # Second Mongo $set stage when unwind not empty
                dico = {}
                for unwind in self._unwind:
                    if not unwind in dico: dico[unwind] = ["$" + unwind]
                    else: dico[unwind] = [dico[unwind]]
                request.append({"$set" : dico})
            if self._project: request.append({"$project" : self._project})      # Mongo $project stage
            return 'aggregation', request

    @property
    def request(self):
        '''
        Getter returning the content of the query or aggregation query to be executed with ESSearch.execute().
        '''
        request_type, request_content = self._fullSearchMongo()

        if request_type == 'find':
            return 'collection.find(' + str(request_content) + ', ' + str(self._project) + ')'
        else:
            return 'collection.aggregate(' + str(request_content) + ')'

    @property
    def cursor(self):
        '''
        Getter returning the cursors of the query or aggregation query result on all collections and cursors contained in self.input.
        '''
        request_type, request_content = self._fullSearchMongo()
        
        cursor_list = []
        for item in self.input[0]: # Determine the result cursor for each element of the input on which a Mongo query makes sense
            if isinstance(item, (Collection, Cursor, CommandCursor)):
                if request_type == 'find':
                    cursor_list.append(item.find(request_content, self._project))
                else:
                    cursor_list.append(item.aggregate(request_content))
        if len(cursor_list) == 1:
            return cursor_list[0]
        else:
            return cursor_list


    def execute(self, returnmode = 'observation', fillvalue = None, name = None, param = None):
        '''
        Executes the request and returns its result, either in one or many Observations.

        *Parameter*

        - **returnmode** : str (default None) - Parameter giving the format of the output:
            - 'unchanged' : output is returned as it is in the database, some operations like operations sepcific to TimeSlot object are not performed;
            - 'observation': Each element is returned as an observation, but original observations aren't recreated;
            - 'idfused': observations whose ids are the same are merged together; 
            - 'single': return a single observation merging all observations together.
        - **fillvalue** :  (default None) - Value to use to fill gaps when observations are merged together.
        - **name** : str (default None) - name of the output observation when returnmode is 'single'.
        - **param** : dict (default None) - param of the output observation when returnmode is 'single'.
        '''
        if returnmode not in {'unchanged', 'observation', 'idfused', 'single'}: raise ValueError("returnmode must have one of these values: 'unchanged', 'observation', 'idfused', 'single'.")
        if returnmode == 'single':
            if name  is not None and not isinstance(name, str)  : raise TypeError("name should be a string.")
            if param is not None and not isinstance(param, dict): raise TypeError("param should be a dictionnary.")
        self._filtered = False # Boolean put to True inside of self._cond() if an additional filtering specific to TimeSlot and shapely geometries is necessary.
        
        ## Construction of a result list where data are in the format given by returnmode
        
        ## ESSearch.execute() 1: Query is executed on each Mongo Collection or Cursor of self.input

        result = []
        for data in self.input[0]:
            request_type, request_content = self._fullSearchMongo()
            if request_type == 'find':
                cursor = data.find(request_content, self._project)
            else:
                cursor = data.aggregate(request_content)

            if returnmode == 'observation': # Only in this case is an observation created directly.
                for item in cursor:
                    if self._filtered: # Additional filtering for objects like TimeSlot who need it
                        for conds in self.parameters:
                            checks_parameters, checks_conds = True, True
                            for cond in conds:
                                if cond['path'] in item:
                                    try: checks_conds = checks_conds and self._condcheck(item[cond['path']], cond) # checking for each condition if it is satisfied
                                    except: checks_conds = False
                                else:
                                    checks_conds = False
                            checks_parameters = checks_parameters or checks_conds
                    dic = {}
                    if '_metadata' in item:
                        if 'name'  in item['_metadata']: dic['name']  = item['_metadata']['name']
                        if 'param' in item['_metadata']: dic['param'] = item['_metadata']['param']
                        del item['_metadata']
                    dic['idxdic'] = {key: [item[key]] for key in item}
                    if not self._filtered or (self._filtered and checks_parameters): result.append(Observation.dic(**dic))

            elif returnmode == 'single':
                for item in cursor:
                    if '_metadata' in item : del item['_metadata']
                    result.append(item)

            else: # returnmode == 'unchanged' or returnmode == 'idfused'
                for item in cursor:
                    if item:
                        result.append(item)

        ## ESSearch.execute() 2: Operations for cases 'idfused' and 'single' are performed on output objects.
        # (more efficient to do it like this than after a conversion to Observation)

        if returnmode == 'single':
            arg = {} # argument to be given to Observation.dic() merging all observations together
            for i in range(len(result)):
                for column_name in arg: # for columns already in the new Observation
                    if column_name not in result[i]:
                        arg[column_name].append(fillvalue)
                for column_name in result[i]: # for columns missing in the new Observation
                    if column_name not in arg:
                        arg[column_name] = [fillvalue] * i + [result[i][column_name]] # an empty column filled with fillvalue is added if a new column name is encountered
                    else:
                        arg[column_name].append(result[i][column_name])
            if self._filtered: result = [self._filtered_observation(Observation.dic(arg))]
            else: result = [Observation.dic(arg)]

        elif returnmode == 'idfused':
            hashs_dic = {}
            for item in result:
                id = str(item['_metadata']['id']) # will throw an error if item has no id. Should items with no id be let as is or merged together?
                if id in hashs_dic: # one line is added to hashs_dic[id] for each element of result having this id
                    del item['_metadata'] # Two items with the same id should have the same metadata.
                    for column_name in hashs_dic[id]['idxdic']:
                        if column_name not in item:
                            hashs_dic[id]['idxdic'][column_name].append(fillvalue)
                    for column_name in item:
                        if column_name not in hashs_dic[id]['idxdic']:
                            hashs_dic[id]['idxdic'][column_name] = [fillvalue] * i + [item[column_name]] # a filled column is added if a new column name is encountered
                        else:
                            hashs_dic[id]['idxdic'][column_name].append(item[column_name])
                else:
                    dic = {}
                    if 'name'  in item['_metadata']: dic['name']  = item['_metadata']['name']
                    if 'param' in item['_metadata']: dic['param'] = item['_metadata']['param']
                    del item['_metadata']
                    dic['idxdic'] = {key: [item[key]] for key in item}
                    hashs_dic[id] = dic
            result = []
            for id in hashs_dic: # an Observation is added to result for each id
                obs_out = Observation.dic(**hashs_dic[id])
                if obs_out:
                    if self._filtered: result.append(self._filtered_observation(obs_out)) # finalement, semble plus pertinent de faire ce filtrage directemt sur la sortie Mongo, car même si un à un les tests de condition sont faits à de nombreuses reprises, au global ce ne sont jamais les mêmes combinaisons de test
                    else: result.append(obs_out)
        # At this point, result is a list of observations.

        ## ESSearch.execute() 3: Other inputs (pure observations) are treated purely in python with the self._filtered_observation() method

        for data in self.input[1]: # data which are not taken from a Mongo database and already are observations are treated here.
            result.append(self._filtered_observation(data, False))

        ## ESSearch.execute() 4: Operations for cases 'idfused' and 'single' are performed again with the added observations

        if len(result) >= 1:
            if returnmode == 'single':
                result = self._fusion(result, fillvalue)
                if name is None: name = "ESSearch query result on " + str(datetime.datetime.now()) # default value for name
                if param is None: # default value for param
                    if self.sources is not None:
                        sources = self.sources
                    else:
                        sources = []
                        for item in self.input: # informations about the inputs are added to param
                            if isinstance(item, Observation):
                                if item.name is not None:
                                    sources.append('Observation: ' + item.name)
                                else:
                                    sources.append('data')
                            elif isinstance(item, Collection):
                                sources.append('MongoDB collection: ' + item.name + ' from database: ' + item.database.name)
                            elif isinstance(item, Cursor):
                                sources.append('Pymongo cursor: ' + item.cursor_id + ' from collection ' + item.collection.name + 
                                                ' from database: ' + item.collection.database.name)
                            elif isinstance(item, CommandCursor):
                                sources.append('Pymongo commandcursor: ' + item.cursor_id + ' from collection ' + item.collection.name + 
                                                ' from database: ' + item.collection.database.name)
                            else: # should not happen
                                sources.append('data')
                    param = {'date': str(datetime.datetime.now()), 'project': 'essearch', 'type': 'dim3', 
                            'context': {'origin': 'ESSearch query', 'sources ': sources, 
                            'ESSearch_parameters': str(self.parameters)}}
                result.param = param

            elif returnmode == 'idfused' and len(result) != 1:
                hashs_dic = {} # This dictionnary is in the format {id: [observations]}
                for item in result:
                    if item.id in hashs_dic:
                        hashs_dic[item.id].append(item)
                    else:
                        hashs_dic[item.id] = [item]
                result = []
                for id in hashs_dic:
                    obs_out = self._fusion(hashs_dic[id], fillvalue)
                    if hashs_dic[id][0].name : obs_out.name = hashs_dic[id][0].name # name and param associated to the id are put back
                    if hashs_dic[id][0].param: obs_out.name = hashs_dic[id][0].param
                    if obs_out: result.append(obs_out)

        ## ESSearch.execute() 5: Return result

        return result

    def _filtered_observation(self, obs, is_from_mongo = True): # Vérifier que cette fonction n'est pas moins efficace que de tout déplier / filtrer / tout replier
        # Regarder si on ne peut pas faire la même chose en mieux avec des fonctions de numpy ou panda.
        '''
        Takes an Observation and returns a filtered Observation with self.parameters as a filter.
        '''
        # self.parameters = [[cond1 AND cond 2 AND cond 3] OR [cond4 AND cond5 AND cond6]]
        # dico = {"data": [["datation", [date1, date2, date3], [0,1,0,2,2,1]], ["location", [loc1, loc2, loc3], [0,1,2,0,1,1]]]} # dico n'est plus utilisé
        if len(obs) == 0 or self.parameters == [[]]: return obs

        ## ESSearch._filtered_observation() 0: This function is done with an iteration over self.parameters 

        final_filter = [False] * obs.lencomplete
        for i in range(len(self.parameters)): # for each group of conditions separated by a or
            if self.parameters[i] != []:

        ## ESSearch._filtered_observation() 1: Checking if no column is missing and if conditions on metadata are verified

                conds = {} # conds is a dict which associates columns to the condition which concern them (inside of [cond1 AND cond 2 AND cond 3] : only AND)
                relevant = True # no column given by cond["path"] is missing from obs
                for cond in self.parameters[i]:
                    next_relevant = False
                    for j in range(len(obs.lindex)):
                        if cond["path"] == obs.lindex[j].name:
                            if j in conds: conds[j].append(cond)
                            else: conds[j] = [cond]
                            next_relevant = True
                        elif cond["path"][:9] == "_metadata": # metadata are id, name and param
                            if not is_from_mongo: # This step is considered to be done already for data taken out of Mongo
                                if cond["path"][10:] == 'name' : next_relevant = next_relevant and self._condcheck(obs.name, cond)
                                if cond["path"][10:] == 'id'   : next_relevant = next_relevant and self._condcheck(obs.id, cond)
                                if cond["path"][10:] == 'param': next_relevant = next_relevant and self._condcheck(obs.param, cond)
                            else:
                                next_relevant = True
                    relevant = relevant and next_relevant
                if not relevant: continue # if a column on which a condition is applied is missing, the set of conditions given by the element of self.parameters is considered not verified.

        ## ESSearch._filtered_observation() 2: Condition is applied on all elements of the Observation to create a boolean filter

                full_filter = [True] * obs.lencomplete
                for j in range(obs.lenidx): # iteration over the columns
                    filter = []
                    for item in obs.lindex[j].cod:
                        boolean = True
                        for cond in conds[j]:
                            try: boolean = boolean and self._condcheck(item, cond)
                            except: pass #boolean = False # pose problème pour les regex et autres opérations non implémentées...
                        filter.append(boolean) # condition is rewritten as a boolean filter for the incoming data
                    next_full_filter = util.tovalues(obs.lindex[j].keys, filter) # filter changed from filter on optimize codec to filter on full codec. (filter on optimize codec was the just how we calculated it, this isn't an actual method of the module)
                    full_filter = [full_filter[k] and next_full_filter[k] for k in range(len(full_filter))] # full filter is updated each time

        ## ESSearch._filtered_observation() 3: or_position is taken into account

                final_filter = [final_filter[j] or full_filter[j] for j in range(len(full_filter))]

        ## ESSearch._filtered_observation() 4: Application of the final filter on the incoming Observation

        obs.setfilter(final_filter)
        obs.applyfilter()
        return obs

    def _condcheck(self, item, cond = None): # ajouter la gestion des regex
        '''
        Takes an item and returns a Boolean if it verifies criteria given by parameter.
        '''
        #cond = {"comparator" : comparator, "operand" : operand, "path" : path} and sometimes can contain other things

        # 0. Basic cases

        if cond is None: return True
        if 'inverted' in cond and cond['inverted']: return not self._condcheck(item, cond | {'inverted' : False})
        if cond["comparator"] is None and cond["operand"] is None: return True

        # 1. formatstring applied if formatstring there is

        if "formatstring" in cond:
            if not isinstance(item, (datetime.datetime, TimeSlot)):
                item = datetime.datetime.strptime(item, cond["formatstring"])
            if not isinstance(cond["operand"], (datetime.datetime, TimeSlot)):
                cond["operand"] = datetime.datetime.strptime(cond["operand"], cond["formatstring"])

        # 2. Cases TimeSlot, geometry and nested property need specific treatment

        if isinstance(item, TimeSlot):
            if isinstance(cond["operand"], TimeSlot): # if comparator is one of the specific operators for TimeSlot
                cond["comparator"] = dico_alias_python[TimeSlot][TimeSlot][cond["comparator"]]
                return item.link(cond["operand"])[0] == cond["comparator"]
            else: # if operand is a datetime
                try: return dico_alias_python[TimeSlot][datetime.datetime][cond["comparator"]](item, cond["operand"])
                except: raise ValueError("Comparator not supported for TimeSlot.")

        elif isinstance(item, list) or isinstance(item, shapely.geometry.base.BaseGeometry):
            if isinstance(item, list): # lists are interpreted as geometries
                if len(item) == 1: item = shapely.geometry.Point(item[0])
                elif (len(item) > 1 and not isinstance(item[0], list)): item = shapely.geometry.Point(item)
                elif len(item) == 2: item = shapely.geometry.LineString(item)
                elif len(item) > 2:
                    if not item[-1] == item[0]:
                        item.append(item[0])
                    item = shapely.geometry.Polygon([item])
            if isinstance(cond["operand"], list): # lists are interpreted as geometries
                if len(cond["operand"]) == 1: cond["operand"] = shapely.geometry.Point(cond["operand"][0])
                elif (len(cond["operand"]) > 1 and not isinstance(cond["operand"][0], list)):
                    cond["operand"] = shapely.geometry.Point(cond["operand"])
                elif len(cond["operand"]) == 2: cond["operand"] = shapely.geometry.LineString(cond["operand"])
                elif len(cond["operand"]) > 2:
                    if not item[-1] == item[0]:
                        item.append(item[0])
                    item = shapely.geometry.Polygon([item])
            return dico_alias_mongo['geometry'][cond["comparator"]](item, cond["operand"])

        elif cond["path"] == "property" and isinstance(item, dict): # assuming that property contains dicts and that the query targets one of its values
            for val in item.values():
                if self._condcheck(val, cond | {"path" : None}):
                    return True
            return False

        # 3. General comparison for remaining cases

        try: return dico_alias_mongo['default'][cond["comparator"]](item, cond["operand"])
        except:
            #raise ValueError("Comparator not supported.")
            return True

    def _fusion(self, obsList, fillvalue = None): # Idéalement, utiliser une méthode fusion de Observation.
        '''
        Takes a list of observations and returns one observation merging them together in one single observation.
        '''
        ## ESSearch._fusion() 0: Basic cases

        if   len(obsList) == 0: return Observation()
        elif len(obsList) == 1: return Observation(obsList[0])
        else: # Fusion of a list with more than one element
            lidx = []

        ## ESSearch._fusion() 1: Determination of the names of the columns

            new_lname = set()
            for obs in obsList:
                new_lname |= set(obs.lname)
            new_lname = list(new_lname)
            
        ## ESSearch._fusion() 2: Fill the columns with the values of the observations to merge

            for i in range(len(new_lname)): # for each column of the new Observation
                values = []
                for obs in obsList: # for each Observation in the list
                    if new_lname[i] in obs.lname: values += obs.lindex[obs.lname.index(new_lname[i])].values # values of the column are added to the new column
                    else: values += [fillvalue] * len(obs) # when there is no value, filled with fillvalue
                codec = util.tocodec(values)
                lidx.append(Iindex(codec, new_lname[i], util.tokeys(values, codec)))

        ## ESSearch._fusion() 3: Build the actual Observation

            return Observation(lidx)
            # Il y aurait peut-être moyen d'optimiser un peu en remplaçant Iindex, util.tokeys et l'appel final d'Observation par des manipulations directes sur les objets.
            # faire la fusion directement sur les keys au lieu de la faire sur les codec ?
            # Avec la méthode actuelle, certaines opérations sont faites plusieurs fois.