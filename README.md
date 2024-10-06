# Fiber-optic-project

## Set-Up
--------------
1. Clone repository on your local computer `git clone git@github.com:yuliiabosher/Fiber-optic-project.git`
2. Open a terminal `CTRL+T` and change directory to the repository. Commands vary depending on the operating system. For Linux use `cd Fiber-optic-project`, For Windows do `dir Fiber-optic-project` (Unless Windows command prompt has changed sinceI Last used it)
3. Install a virtual environment module `pip install virtualenv`. The dependencies pinned are for python3.8 so do `python --version` to ensure the python version is the same (We can update to a newer Python version Later)
4. Create the virtual environment with `python -m virtualenv env`
5. Acivate the virtual environment `source env/bin/activate`
6. Install dependencies `pip install -r requirements.txt`

## Utility Functions
------------------------

1. With an Open Terminal and an active virtual environment as described in the set-up. Change directory to the utilities folder `cd Utilities` or `dir Utilities`
2. Run the script with `python search_europe.py --api_keys=api_key1,api_key2

Extra flags can be used. See `python search_europe.py --help`  
- --api_keys : Specify API Keys to be used (More than One MUST be specified)
- --tags : Specify tags to be used, separated with a comma 
- --file_format: Specify the file format for the json files to saved in (Must be enclosed with single speech marks and contain ${country} in the name
- --map_name: Specify what you want the map to be called, must have an html extension

Example Usuage: `python test.py --api_keys=api_key1,api_key2 --tags man_made=street_cabinet,street_cabinet=fiber --map_name map2.html --file_format '${country}_fiber_cabinets.json' `

Json files containing the data will be saved in the Utility folder, A map will be generated as an html file showing the coverage of the search
