# Project 

# This repository contains the source code for the project "Decision Brain" of task assignment.

## Execution Instructions

# Also, make sure to install the required dependencies by executing the following command:

pip install -r requirements.txt

### Phase 1

# Before running the code `Models/phase1.py`, make sure to modify the import paths as follows:

# 1. In this case, replace it with the absolute path of the project:

import sys
sys.path.insert(0, "/absolute/path/to/your/project")  # Line 9

# 2. For the relative path of the instance (the relative path for Mac is different from the relative path on Windows):

Tasks, Employees, task_availabilities = read_excel_to_dict("Instances/instance_name.xlsx", True) # Line 250

### Phase 2

# Before running the code `Models/phase2.py`, make sure to modify the import paths as follows:

# 1. In this case, replace it with the absolute path of the project:

sys.path.insert(0, "/absolute/path/to/your/project") # Line 8 + Line 13

# 2. For the relative path of the instance (the relative path for Mac is different from the relative path on Windows):

Tasks, Employees, availabilities = read_excel_to_dict("Instances/instance_name.xlsx", False ) # Line 518

### Phase 3 - Metaheuristics

# Before running the code `Models/Metaheuristics/main.py`, make sure to modify the import paths as follows:

# 1. In this case, replace it with the absolute path of the project:

sys.path.insert(0, "/absolute/path/to/your/project/Models") # Line 11 #main.py  
sys.path.insert(0, "/absolute/path/to/your/project") # Line 6 #utils.py  
sys.path.insert(0, "/absolute/path/to/your/project") # Line 8 #mutation.py  

# 2. For the relative path of the instance (the relative path for Mac is different from the relative path on Windows), modify it directly in the main function of main.py

# The run_model function takes as input the initial number of solutions in the population, the instance file name, the mutation rate, and alpha
