# Intro

This project has been created to assist my dissertation project _Identifying critical source code at method level 
by performing threshold-based and clustering algorithms on software metrics_.


# Prototype application
The application is written using [Dash and Plotly](https://dash.plotly.com/). 
Some of the elements and style used in this application are from their tutorials and examples.

There is sample data for metrics available in the repository, however, more data set can be added.
In the folder **tool/data** add the more directories following the pattern:

* project/
* &nbsp;&nbsp;&nbsp;&nbsp; metrics.csv
* &nbsp;&nbsp;&nbsp;&nbsp; test_coverage.csv

The app will read all the directories under **data** and will display the list of them on the index page.


## Run with docker
Using the Dockerfile from the project's root location.

Build the container using a name
```
docker build -t clust-dash:1.0 .
```

Then run it (this commands will run the container in background)
```
docker run --rm -d -p 80:8050 clust-dash:1.0
```

Then the application should be available at ```localhost``` on the default port 80.

## Run locally
In the file tool/app.py, uncomment the lines below *Use to run locally*, and comment those for Docker env.

Run the module, and the application should be available at ```localhost:8051```.


# Repository mining
The repository mining program was implemented based on [PyDriller](https://pydriller.readthedocs.io/en/latest/). 
```
changesmining
```

# Data reading and preparation
The source code metrics, commits, profiling, test coverage reports are read and the method signatures 
are modified to create a single data set.
```
datareading
```

# Data analysis
Contains the process to analyse the data set metrics, perform the clustering algorithms and validation strategy.
```
dataanalysis
```
