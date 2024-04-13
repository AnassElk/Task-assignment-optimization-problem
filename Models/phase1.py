import math
import sys
from datetime import datetime, timedelta

import geopy.distance
from gurobipy import *

sys.path.insert(0, "C:/Users/anass/Documents/ST-74_Decision_Brain/")
from Extraction.extraction import TaskType, read_excel_to_dict
from Models.output import (generate_plot_gantt_diagram,
                           generate_plot_map_of_employees,
                           generate_plot_map_of_employees_with_arrows,
                           generate_solution_file, get_employee_name_by_index)


def time_to_duration(time_str):
    parsed_time = datetime.strptime(time_str, "%I:%M%p")

    reference_time = parsed_time.replace(hour=0, minute=0, second=0)

    time_difference = parsed_time - reference_time

    duration_in_minutes = time_difference.total_seconds() / 60

    return int(duration_in_minutes)


def travel_time(a, b):
    coords_1 = (a.latitude, a.longitude)
    coords_2 = (b.latitude, b.longitude)
    return math.ceil(((geopy.distance.geodesic(coords_1, coords_2).km) * 60 / 50))

def travel_time_lat_long(latitude1, longitude1, latitude2, longitude2):
    coords_1 = (latitude1, longitude1)
    coords_2 = (latitude2, longitude2)
    return math.ceil(((geopy.distance.geodesic(coords_1, coords_2).km) * 60 / 50))
 
def var_model_phase1(Tasks, Employees): 
    # m : Model
    m = Model("PL1")
    num_employees = len(Employees)
    num_tasks = len(Tasks)
    
    # -- Ajout de la variable Xijk  --
    # x : Var
    x = {
        (i, j, k): m.addVar(vtype=GRB.BINARY, name="x{i}{j}{k}")
        for i in range(num_tasks)
        for j in range(num_tasks)
        for k in range(num_employees)
    }

    # xii = 0
    for i in range(num_tasks):
        for k in range(num_employees):
            m.addConstr(x[i, i, k] == 0)

    t = {(i): m.addVar(vtype=GRB.INTEGER, name="T{i}") for i in range(num_tasks)}

    # Constraint #1: only one possible path in the input of each task
    for i in range(num_tasks):
        if Tasks[i].type != TaskType.ARRIVALS:
            m.addConstr(
                quicksum(
                    x[i, j, k]
                    for j in range(num_tasks)
                    for k in range(num_employees)
                    if Tasks[j].type != TaskType.DEPARTURES
                )
                == 1
            )

    # Constraint #2: only one possible path in the output of each task
    for j in range(num_tasks):
        if Tasks[j].type != TaskType.DEPARTURES:
            m.addConstr(
                quicksum(
                    x[i, j, k]
                    for i in range(num_tasks)
                    for k in range(num_employees)
                    if Tasks[i].type != TaskType.ARRIVALS
                )
                == 1
            )

    # Constraint #3: skill level constraint
    for k in range(num_employees):
        for i in range(num_tasks):
            m.addConstr(
                Employees[k].level * quicksum(x[i, j, k] for j in range(num_tasks))
                >= Tasks[i].level * quicksum(x[i, j, k] for j in range(num_tasks))
            )

    # # Constraint #4: taks start/end time:
    for i in range(num_tasks):
        m.addConstr(t[i] >= Tasks[i].opening_time)

    for i in range(num_tasks):
        m.addConstr(t[i] <= Tasks[i].closing_time - Tasks[i].duration)

    # Constraint #5: relation task task:
    M = 1000000
    for i in range(num_tasks):
        for j in range(num_tasks):
            binary_variable = quicksum(x[i, j, k] for k in range(num_employees))
            m.addConstr(
                t[j]
                >= t[i]
                + Tasks[i].duration
                + travel_time(Tasks[i], Tasks[j])
                - M * (1 - binary_variable),
                name=f"relation_task_{i}_task_{j}",
            )

    # # constraint #6: unavailabilities:
    for i in range(num_tasks):
        if Tasks[i].type == TaskType.UNAVAILABILITIES:
            m.addConstr(
                quicksum(
                    x[i, j, Tasks[i].employee_id]
                    for j in range(num_tasks)
                    if Tasks[j].type != TaskType.DEPARTURES
                )
                == 1
            )
            m.addConstr(
                quicksum(
                    x[j, i, Tasks[i].employee_id]
                    for j in range(num_tasks)
                    if Tasks[j].type != TaskType.ARRIVALS
                )
                == 1
            )

    # # constraint #7: departures:
    for i in range(num_tasks):
        if Tasks[i].type == TaskType.DEPARTURES:
            m.addConstr(
                quicksum(x[i, j, Tasks[i].employee_id] for j in range(num_tasks)) == 1
            )

    # # constraint #8: arrivals:
    for i in range(num_tasks):
        if Tasks[i].type == TaskType.ARRIVALS:
            m.addConstr(
                quicksum(
                    x[j, i, Tasks[i].employee_id]
                    for j in range(num_tasks)
                    if Tasks[j].type != TaskType.ARRIVALS
                )
                == 1
            )

    for k in range(num_employees):
        for j in range(num_tasks):
            if (
                Tasks[j].type != TaskType.ARRIVALS
                and Tasks[j].type != TaskType.DEPARTURES
            ):
                m.addConstr(
                    quicksum(x[i, j, k] for i in range(num_tasks))
                    == quicksum(
                        (x[j, z, k])
                        for z in range(num_tasks)
                        if Tasks[z].type != TaskType.DEPARTURES
                    )
                )

    m.setObjective(
        quicksum(
            x[i, j, k] * travel_time(Tasks[i], Tasks[j])
            for i in range(num_tasks)
            for j in range(num_tasks)
            for k in range(num_employees)
        ),
        GRB.MINIMIZE,
    )
    
    m.setParam("Timelimit", 1400)
    m.update()
    m.optimize()
    total_cost = m.ObjVal
    generate_solution_file(x, t, Tasks, Employees, "Solution.txt",True)
    task_table = [t[i].Xn for i in range(num_tasks) if Tasks[i].type == TaskType.NORMAL]
    employee_tasks = {
        get_employee_name_by_index(Employees, k): [] for k in range(num_employees)
    }
    employee_travel_time = {
                get_employee_name_by_index(Employees, k): []
                for k in range(num_employees)
            }
    for k in range(num_employees):
        employee_name = get_employee_name_by_index(Employees, k)
        for i in range(num_tasks):
            for j in range(num_tasks):
                if x[i, j, k].x == 1:
                    employee_tasks[employee_name].append(
                        (i, t[i].Xn, Tasks[i].duration, Tasks[i].latitude, Tasks[i].longitude )
                    )
                    if Tasks[j].type == TaskType.ARRIVALS:
                        employee_tasks[employee_name].append(
                            (j, t[j].Xn, Tasks[j].duration, Tasks[j].latitude, Tasks[j].longitude)
                        )
    for employee_name, tasks in employee_tasks.items():
                sorted_tasks = sorted(tasks, key=lambda x: x[1])
                for i, (id, start_time, duration, latitude, longitude) in enumerate(sorted_tasks[1:]):
                        travel_time_start = sorted_tasks[i][1] + sorted_tasks[i][2]
                        if travel_time_start != start_time:
                            employee_travel_time[employee_name].append((travel_time_start, travel_time_start + travel_time_lat_long(latitude, longitude, sorted_tasks[i][3], sorted_tasks[i][4])))
    map_of_employees = []
    for k in range(num_employees):
        map_of_employee_k = []
        map_of_employee_k.append((Employees[k].longitude, Employees[k].latitude, -1))
        dict_movement = {
            i: j
            for i in range(num_tasks)
            for j in range(num_tasks)
            if (x[i, j, k].X == 1 and Tasks[i].type != TaskType.DEPARTURES)
        }
        dates_of_movement = {t[i].Xn: i for i in dict_movement.keys()}
        date_of_start = min(dates_of_movement.keys())
        start_index = dates_of_movement[date_of_start]
        while t[start_index].Xn != max(dates_of_movement.keys()):
            if Tasks[start_index].type==TaskType.NORMAL:
                map_of_employee_k.append(
                    (
                        Tasks[start_index].longitude,
                        Tasks[start_index].latitude,
                        Tasks[start_index].id,
                    )
                )
            elif Tasks[start_index].type==TaskType.UNAVAILABILITIES:
                map_of_employee_k.append(
                    (
                        Tasks[start_index].longitude,
                        Tasks[start_index].latitude,
                        'U',
                    )
                )
            start_index = dict_movement[start_index]
        map_of_employee_k.append((Employees[k].longitude, Employees[k].latitude, -1))
        map_of_employees.append(map_of_employee_k)

    return (task_table, map_of_employees, total_cost, employee_tasks, employee_travel_time)

        
def run_model():
    Tasks, Employees, task_availabilities = read_excel_to_dict("Instances\InstanceFinlandV1.xlsx", True)
    task_table, map_of_employees, total_cost, employee_tasks, employee_travel_time = var_model_phase1(
        Tasks, Employees
    )
    generate_plot_map_of_employees_with_arrows(Tasks, map_of_employees)
    generate_plot_gantt_diagram(employee_tasks, employee_travel_time, Tasks)
    generate_plot_map_of_employees(Employees,map_of_employees)

    return map_of_employees, Tasks


if __name__ == "__main__":
    run_model()
