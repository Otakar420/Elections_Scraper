# Elections Scraper

## Project Description
This script extracts results from the parliamentary elections in the Czech Republic
in 2017 based on the selected territorial unit. You can choose any territorial unit
from this [link](https://volby.cz/pls/ps2017nss/ps3?xjazyk=CZ).

## Library Installation
The libraries used in the code are stored in the `requirements.txt` file.
It is recommended to install them using a new virtual environment.
Run the following commands with your package manager:

```python
$ pip3 --version                    # check the version of the package manager
$ pip3 install -r requirements.txt  # install the libraries
```

## Running the Project
Running the `election_scraper.py` file from the command line requires two mandatory arguments:

```python
$ python election_scraper.py <territorial_unit_url_in_quotes> <output_file_name>
```

Subsequently, the results will be downloaded into the "Results" folder as a .csv file, and a graph showing
the top 10 political parties with the highest number of votes will be created as a .png file.

## Project Demonstration
Example of running the project for the Benešov district:
1. Argument: `"https://volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2101"`
2. Argument: `benesov`


### Command to execute the program:
```python
python elections-scraper.py "https://volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2101" benesov
```

### Progress of downloading:
```
DOWNLOADING DATA FROM THE SELECTED URL: 'https://volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=2&xnumnuts=2101'
Scraping districts informations: 100% |████████████████████████████████████████████| 114/114 [00:00]
CSV FILE SUCCESSFULLY CREATED: 'benesov.csv'
BAR PLOT SUCCESSFULLY CREATED: 'Top_10_Parties_of_benesov.png'
PROCESS SUCCESSFULLY FINISHED
```

### Partial Output:
```
code,location,count_registered,count_envelopes,count_valid,...
529303, Benešov,13104,8485,8437,1052,10,2,624,3,802,597,109,35,112,6,11,948,3,6,414,2577,3,21,314,5,58,17,16,682,10
532568, Bernartice,191,148,148,4,0,0,17,0,6,7,1,4,0,0,0,7,0,0,3,39,0,0,37,0,3,0,0,20,0
530743, Bílkovice,170,121,118,7,0,0,15,0,8,18,0,2,0,0,0,3,0,0,2,47,1,0,6,0,0,0,0,9,0
532380, Blažejovice,96,80,77,6,0,0,5,0,3,11,0,0,3,0,0,5,1,0,0,29,0,0,6,0,0,0,0,8,0
...
```