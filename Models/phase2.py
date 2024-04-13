import math
import sys

import matplotlib.pyplot as plt
from geopy.distance import geodesic
from gurobipy import *

sys.path.insert(0, "C:/Users/anass/Documents/ST-74_Decision_Brain")
from Extraction.extraction import TaskType, read_excel_to_dict
from Models.output import (generate_plot_gantt_diagram,
                           generate_plot_map_of_employees,
                           generate_plot_map_of_employees_with_arrows,
                           generate_solution_file)
from Models.phase1 import (get_employee_name_by_index, travel_time,
                           travel_time_lat_long)

# sys.path.insert(0, "c:/Users/yassi/Desktop/projet ST7/ST-74_Decision_Brain")


def var_model_phase2(Tasks, Employees, Tasks_slots):  # dict(string : liste tasks)
    # m : Model
    m = Model("PL1")
    num_employees = len(Employees)
    num_tasks = len(Tasks)
    num_tasks_slots = len(Tasks_slots)
    # -- Ajout de la variable Xijk  --
    # x : Var
    x = {
        (i, j, k): m.addVar(vtype=GRB.BINARY, name="x{i}{j}{k}")
        for i in range(num_tasks)
        for j in range(num_tasks)
        for k in range(num_employees)
    }

    t = {(i): m.addVar(vtype=GRB.INTEGER, name="T{i}") for i in range(num_tasks)}

    y = {
        (i, j, j1, Tasks[j].employee_id): m.addVar(
            vtype=GRB.BINARY, name="y{i}{j}{j1}{k}"
        )
        for i in range(num_tasks)
        for j in range(num_tasks)
        for j1 in range(num_tasks)
        if Tasks[j].type == TaskType.BREAK
    }

    h = {
        (i, w): m.addVar(vtype=GRB.BINARY, name="h{i}{w}")
        for i in range(num_tasks)
        for w in range(len(Tasks_slots[i]))
    }

    # xii = 0
    for i in range(num_tasks):
        for k in range(num_employees):
            m.addConstr(x[i, i, k] == 0)

    # Constraint #1: only one possible path in the input of each task
    for i in range(num_tasks):
        m.addConstr(
            quicksum(x[i, j, k] for j in range(num_tasks) for k in range(num_employees))
            <= 1
        )

    # Constraint #2: can't end with a departure
    for i in range(num_tasks):
        m.addConstr(
            quicksum(
                x[i, j, k]
                for j in range(num_tasks)
                for k in range(num_employees)
                if Tasks[j].type == TaskType.DEPARTURES
            )
            == 0
        )

    # Constraint #3: can't start with an arrival
    for i in range(num_tasks):
        m.addConstr(
            quicksum(
                x[i, j, k]
                for j in range(num_tasks)
                for k in range(num_employees)
                if Tasks[i].type == TaskType.ARRIVALS
            )
            == 0
        )
    # Constraint #4: only one possible path in the output of each task
    for j in range(num_tasks):
        m.addConstr(
            quicksum(x[i, j, k] for i in range(num_tasks) for k in range(num_employees))
            <= 1
        )
    # Constraint #5: skill level constraint
    for k in range(num_employees):
        for i in range(num_tasks):
            m.addConstr(
                Employees[k].level * quicksum(x[i, j, k] for j in range(num_tasks))
                >= Tasks[i].level * quicksum(x[i, j, k] for j in range(num_tasks))
            )

    # Constraint #6: taks start/end time:
    for i in range(num_tasks):
        m.addConstr(t[i] >= Tasks[i].opening_time)

    for i in range(num_tasks):
        m.addConstr(t[i] <= Tasks[i].closing_time - Tasks[i].duration)

    # Constraint #7: relation task task:
    M = 1000000
    for i in range(num_tasks):
        for j in range(num_tasks):
            binary_variable = quicksum(x[i, j, k] for k in range(num_employees))
            if Tasks[i].type != TaskType.BREAK and Tasks[j].type != TaskType.BREAK:
                m.addConstr(
                    t[j]
                    >= t[i]
                    + Tasks[i].duration
                    + travel_time(Tasks[i], Tasks[j])
                    - M * (1 - binary_variable),
                    name="relation_task_{i}_task_{j}",
                )

    # Constraint #8: unavailabilities:
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

    # Constraint #9: departures:
    for i in range(num_tasks):
        if Tasks[i].type == TaskType.DEPARTURES:
            m.addConstr(
                quicksum(x[i, j, Tasks[i].employee_id] for j in range(num_tasks)) == 1
            )

    # Constraint #10: arrivals:
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

    # Constraint #11: linkbetween x and y:
    for i in range(num_tasks):
        for j in range(num_tasks):
            for j1 in range(num_tasks):
                if Tasks[j].type == TaskType.BREAK:
                    if (
                        Tasks[i].type != TaskType.BREAK
                        and Tasks[j1].type != TaskType.BREAK
                    ):
                        m.addConstr(
                            y[i, j, j1, Tasks[j].employee_id]
                            <= x[i, j, Tasks[j].employee_id]
                        )
                        m.addConstr(
                            y[i, j, j1, Tasks[j].employee_id]
                            <= x[j, j1, Tasks[j].employee_id]
                        )
    for j in range(num_tasks):
        if Tasks[j].type == TaskType.BREAK:
            m.addConstr(
                quicksum(
                    y[i, j, j1, Tasks[j].employee_id]
                    for i in range(num_tasks)
                    for j1 in range(num_tasks)
                    if (
                        Tasks[i].type != TaskType.BREAK and Tasks[j1].type != TaskType.BREAK
                    )
                )
                == 1
            )
    # Constraint #11: break j between task i and j1:
    for i in range(num_tasks):
        for j in range(num_tasks):
            for j1 in range(num_tasks):
                if Tasks[j].type == TaskType.BREAK:
                    if (
                        Tasks[i].type != TaskType.BREAK
                        and Tasks[j1].type != TaskType.BREAK
                    ):
                        m.addConstr(
                            t[j1]
                            >= t[i]
                            + Tasks[i].duration
                            + travel_time(Tasks[i], Tasks[j1])
                            + Tasks[j].duration
                            - M * (1 - y[i, j, j1, Tasks[j].employee_id]),
                            name="break {j} between task {i} and {j1}",
                        )
                        print("travel time", travel_time(Tasks[i], Tasks[j1]), i, j1)
                        print("+ Tasks[j].duration", +Tasks[j].duration)
                        print("------------------------")

    # Constraint #12: break after task i :
    for i in range(num_tasks):
        for j in range(num_tasks):
            if Tasks[j].type == TaskType.BREAK:
                m.addConstr(
                    t[j]
                    >= t[i]
                    + Tasks[i].duration
                    - M * (1 - x[i, j, Tasks[j].employee_id]),
                    name="break {j} after task {i}",
                )

    # Constraint #13: break before task j1 :
    for j1 in range(num_tasks):
        for j in range(num_tasks):
            if Tasks[j].type == TaskType.BREAK:
                m.addConstr(
                    t[j]
                    <= t[j1]
                    - Tasks[j].duration
                    + M * (1 - x[j, j1, Tasks[j].employee_id]),
                    name="break {j} before task {j1}",
                )

    # Constraint #14: Breaks must be done:
    for i in range(num_tasks):
        if Tasks[i].type == TaskType.BREAK:
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
    # Constraint #15: tasks unavailibilities
    for i in range(num_tasks):
        for w in range(len(Tasks_slots[i])):
            m.addConstr(
                Tasks_slots[i][w][0] <= t[i] + M * (1 - h[i, w]),
                name="constraint for start_time_Task_{i}_slot_{w}",
            )

            # Constraint #16: tasks unavailibilities
            m.addConstr(
                Tasks_slots[i][w][1] >= Tasks[i].duration + t[i] - M * (1 - h[i, w]),
                name="constraint for end_time_Task_{i}_slot_{w}",
            )

        # Constraint #17: tasks unavailibilities
        m.addConstr(
            quicksum(x[i, j, k] for j in range(num_tasks) for k in range(num_employees))
            == quicksum(h[i, w] for w in range(len(Tasks_slots[i])))
        )

    travel_time_objective = quicksum(
        x[i, j, k] * travel_time(Tasks[i], Tasks[j])
        for i in range(num_tasks)
        for j in range(num_tasks)
        for k in range(num_employees)
        if Tasks[i].type != TaskType.BREAK and Tasks[j].type != TaskType.BREAK
    ) + quicksum(
        y[i, j, j1, Tasks[j].employee_id] * travel_time(Tasks[i], Tasks[j1])
        for i in range(num_tasks)
        for j in range(num_tasks)
        for j1 in range(num_tasks)
        if Tasks[j].type == TaskType.BREAK
    )

    tasks_objective = quicksum(
        x[i, j, k] * (Tasks[i].duration)
        for i in range(num_tasks)
        for j in range(num_tasks)
        for k in range(num_employees)
        if Tasks[i].type == TaskType.NORMAL
    )

    alpha_table = [i / 10 for i in range(0, 11)]
    solution_table = []

    for alpha in alpha_table:
        m.setObjective(
            (1 - alpha) * tasks_objective - alpha * travel_time_objective, GRB.MAXIMIZE
        )

        m.setParam("Timelimit", 300)
        m.update()

        m.optimize()

        for i in range(num_tasks):
            for j in range(num_tasks):
                for j1 in range(num_tasks):
                    if Tasks[j].type == TaskType.BREAK:
                        if y[i, j, j1, Tasks[j].employee_id].x > 0.5:
                            print(
                                f"y {i}, {j}, {j1} == {y[i,j,j1,Tasks[j].employee_id].x}"
                            )

        print_assignment_results(m, x, t, Tasks, Employees)
        generate_solution_file(x, t, Tasks, Employees, "Solution.txt",True)
        sol = (
            round(tasks_objective.getValue(), 2),
            round(travel_time_objective.getValue(), 2),
        )
        print("La solution trouvée pour l'alpha {} est : {}".format(alpha, sol))
        solution_table.append((alpha, sol[0], sol[1]))

        if alpha in [0.3, 0.7]:
            total_cost = sol
            generate_solution_file(
                x, t, Tasks, Employees, "Solution_alpha{}.txt".format(alpha),True
            )
            task_table = [
                t[i].Xn for i in range(num_tasks) if Tasks[i].type == TaskType.NORMAL
            ]
            employee_tasks = {
                get_employee_name_by_index(Employees, k): []
                for k in range(num_employees)
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
                    if Tasks[id].type == TaskType.BREAK:
                        continue
                    elif Tasks[sorted_tasks[i][0]].type == TaskType.BREAK:
                        total_travel_time = travel_time_lat_long(latitude, longitude, sorted_tasks[i-1][3], sorted_tasks[i-1][4])
                        if  sorted_tasks[i][1] == sorted_tasks[i-1][1] + sorted_tasks[i-1][2]:
                            employee_travel_time[employee_name].append((sorted_tasks[i][1] + sorted_tasks[i][2], sorted_tasks[i][1] + sorted_tasks[i][2] + total_travel_time))
                        else:
                            if start_time == sorted_tasks[i][1] + sorted_tasks[i][2]:
                                employee_travel_time[employee_name].append((sorted_tasks[i-1][1] + sorted_tasks[i-1][2], sorted_tasks[i-1][1] + sorted_tasks[i-1][2] + total_travel_time))
                            else:
                                if total_travel_time <= sorted_tasks[i][1] - sorted_tasks[i-1][1] - sorted_tasks[i-1][2]:
                                    employee_travel_time[employee_name].append((sorted_tasks[i-1][1] + sorted_tasks[i-1][2], sorted_tasks[i-1][1] + sorted_tasks[i-1][2] + total_travel_time))
                                else:
                                    remaining_travel_time = total_travel_time - sorted_tasks[i][1] + sorted_tasks[i-1][1] + sorted_tasks[i-1][2]
                                    employee_travel_time[employee_name].append((sorted_tasks[i-1][1] + sorted_tasks[i-1][2], sorted_tasks[i][1]))
                                    employee_travel_time[employee_name].append((sorted_tasks[i][1] + sorted_tasks[i][2], sorted_tasks[i][1] + sorted_tasks[i][2] + remaining_travel_time))

                    else:    
                        travel_time_start = sorted_tasks[i][1] + sorted_tasks[i][2]
                        if travel_time_start != start_time:
                            employee_travel_time[employee_name].append((travel_time_start, travel_time_start + travel_time_lat_long(latitude, longitude, sorted_tasks[i][3], sorted_tasks[i][4])))
            map_of_employees = []
            for k in range(num_employees):
                map_of_employee_k = []
                map_of_employee_k.append(
                    (Employees[k].longitude, Employees[k].latitude, -1)
                )
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
                    if Tasks[start_index].type == TaskType.NORMAL:
                        map_of_employee_k.append(
                            (
                                Tasks[start_index].longitude,
                                Tasks[start_index].latitude,
                                Tasks[start_index].id,
                            )
                        )
                    elif Tasks[start_index].type == TaskType.UNAVAILABILITIES:
                        map_of_employee_k.append(
                            (
                                Tasks[start_index].longitude,
                                Tasks[start_index].latitude,
                                "U",
                            )
                        )
                    elif Tasks[start_index].type == TaskType.BREAK:
                        map_of_employee_k.append(
                            (
                                Tasks[start_index].longitude,
                                Tasks[start_index].latitude,
                                "B",
                            )
                        )
                    start_index = dict_movement[start_index]
                if Tasks[start_index].type == TaskType.NORMAL:
                    map_of_employee_k.append(
                        (
                            Tasks[start_index].longitude,
                            Tasks[start_index].latitude,
                            Tasks[start_index].id,
                        )
                    )
                elif Tasks[start_index].type == TaskType.UNAVAILABILITIES:
                    map_of_employee_k.append(
                        (
                            Tasks[start_index].longitude,
                            Tasks[start_index].latitude,
                            "U",
                        )
                    )
                elif Tasks[start_index].type == TaskType.BREAK:
                    map_of_employee_k.append(
                        (
                            Tasks[start_index].longitude,
                            Tasks[start_index].latitude,
                            "B",
                        )
                    )
                map_of_employee_k.append(
                    (Employees[k].longitude, Employees[k].latitude, -1)
                )
                for i in range(len(map_of_employee_k)):
                    if map_of_employee_k[i][2] == "B":
                        map_of_employee_k[i] = interpolate_coordinates(
                            map_of_employee_k[i - 1][0],
                            map_of_employee_k[i - 1][1],
                            map_of_employee_k[i + 1][0],
                            map_of_employee_k[i + 1][1],
                            0.5,
                        )
                map_of_employees.append(map_of_employee_k)
            print(map_of_employees)
            generate_plot_map_of_employees_with_arrows(Tasks, map_of_employees)
            generate_plot_map_of_employees(Employees, map_of_employees)
            generate_plot_gantt_diagram(employee_tasks, employee_travel_time, Tasks)

    Z1 = [sol[1] for sol in solution_table]
    Z0 = [sol[0] for sol in solution_table]
    Z2 = [sol[2] for sol in solution_table]
    k = 1
    for alpha, i, j in zip(Z0, Z1, Z2):
        plt.scatter(i, j, marker=".", label=str((i, j)))
        plt.annotate(str(alpha), (i, j))
        k += 1

    plt.grid(linestyle="--", color="gray")
    plt.xlim((0, 2500))
    plt.ylim((0, 2500))

    plt.xlabel("Travel distance")
    plt.ylabel("Perturbation pondérée")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.show()

    return (task_table, map_of_employees, total_cost, employee_tasks)


def interpolate_coordinates(lon1, lat1, lon2, lat2, fraction):
    total_distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers

    if total_distance == 0:
        return (lon1, lat1, "B")

    fraction_distance = fraction * total_distance

    intermediate_point_lat = lat1 + (lat2 - lat1) * (fraction_distance / total_distance)
    intermediate_point_lon = lon1 + (lon2 - lon1) * (fraction_distance / total_distance)

    return (intermediate_point_lon, intermediate_point_lat, "B")


def run_model():
    Tasks, Employees, availabilities = read_excel_to_dict(
        "Instances\InstancePolandV2.xlsx",False
    )
    task_table, map_of_employees, total_cost, employee_tasks = var_model_phase2(
        Tasks, Employees, availabilities
    )

    return Tasks


def print_assignment_results(m, x, t, Tasks, Employees):
    num_employees = len(Employees)
    num_tasks = len(Tasks)

    for i in range(num_tasks):
        for j in range(num_tasks):
            for k in range(num_employees):
                if x[i, j, k].x > 0.5:
                    print(f"Employee {k} performs Task {i} and then Task {j}")

    for i in range(num_tasks):
        print(f"Task {i} starts at time {t[i].x}")


if __name__ == "__main__":
    run_model()
