# Getting Started

The code used, the results and the explanations are provided through "Jupyter 
Notebook" indicated in link in each chapter.
The Notebook files are 
<a href="https://github.com/loco-philippe/loco-philippe.github.io/tree/main/Example" target="_blank">
stored in Github</a> and can be replayed.

The Jupyter Notebooks with map are available on [nbviewer](http://nbviewer.org/github/loco-philippe/Environmental-Sensing/tree/main/python/Examples/Observation/)

## First Observation

This [chapter](./first_observation.ipynb) explain you:
    
- how to create a simple and more complex Observation Object
- the different view of the data
- how the ObsJSON is structured 

## Observation for sensor

A sensor sends data to a server with a specific protocol. The server stores and processes the data.
The sensor how use TCP/IP sends the data with ObsJSON format (see above).
This [chapter](./sensor_observation.ipynb) introduces you to the to binary interface and explain you:
    
- how to encode and decode binary data
- the processes to obtain low data as explain in the "Binary interface" chapter

## Dimension concept

The dimension is an important concept to understand (see chapter above). 

In [this example](./dimension.ipynb), we show you Observations with differents dimensions (1 to 3).

We also present how Result values without index can be loaded with the 'order' parameter.
    
## Observation management

*Under construction*

# Quick overview

*Under construction*

## Create an Observation

*Under construction*

- Measuring station
- Mobile sensor
- Simulation
- Access information
- Visualize an Observation

## Generate an Exchange format

*Under construction*

- Binary format
- Json format
- No SQL format

## Managing Observations

*Under construction*

- Add
- Sort
- Filter
- Aggregation

## Interface

*Under construction*

- Numpy export
- Xarray export
- File storage
