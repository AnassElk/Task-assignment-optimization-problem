import copy
import math as m
import random as rd

import matplotlib.pyplot as plt
from utils import (
    append_break_task,
    append_task,
    find_home,
    find_unavailabilty,
    get_employee_name_by_index,
    is_schedule_feasible,
    is_unavailability_done,
    travel_time,
)

from Extraction.extraction import TaskType
from Models.phase2 import interpolate_coordinates


def create_individual(Tasks, Employees):
    individual = {employee: [] for employee in Employees}
    Normal_Tasks = [
        Tasks[i] for i in range(len(Tasks)) if Tasks[i].type == TaskType.NORMAL
    ]
    Unavailability_Tasks = [
        [
            Tasks[j]
            for j in range(len(Tasks))
            if Tasks[j].type == TaskType.UNAVAILABILITIES and Tasks[j].employee_id == i
        ]
        for i in range(len(Employees))
    ]
    Departure_Tasks = [
        Tasks[i] for i in range(len(Tasks)) if Tasks[i].type == TaskType.DEPARTURES
    ]
    Arrival_Tasks = [
        Tasks[i] for i in range(len(Tasks)) if Tasks[i].type == TaskType.ARRIVALS
    ]
    Break_Tasks = [
        Tasks[i] for i in range(len(Tasks)) if Tasks[i].type == TaskType.BREAK
    ]
    distance_tasks = (
        Normal_Tasks
        + Departure_Tasks
        + Arrival_Tasks
        + [
            Tasks[j]
            for j in range(len(Tasks))
            if Tasks[j].type == TaskType.UNAVAILABILITIES
        ]  # unavailability à changer
    )
    initial_individual = {employee: [] for employee in Employees}
    distance_matrix = [[0] * (len(Tasks) - len(Break_Tasks))] * (
        len(Tasks) - len(Break_Tasks)
    )
    for i in range(len(distance_matrix)):
        for j in range(len(distance_matrix[0])):
            distance_matrix[i][j] = travel_time(distance_tasks[i], distance_tasks[j])
    remaining_Tasks = copy.deepcopy(Normal_Tasks)
    for i in range(len(Employees)):
        employee = Employees[i]
        initial_individual[employee] = []
        for j in range(len(Departure_Tasks)):
            if Departure_Tasks[j].employee_id == i:
                initial_individual[employee].append(Departure_Tasks[j])
                individual[employee].append(Departure_Tasks[j])

        for j in range(len(Unavailability_Tasks[i])):
            initial_individual[employee].append(Unavailability_Tasks[i][j])

        for j in range(len(Departure_Tasks)):
            if Arrival_Tasks[j].employee_id == i:
                initial_individual[employee].append(Arrival_Tasks[j])
        Lunch = False
        scheldules_of_employee = [
            (initial_individual[employee][i], initial_individual[employee][i + 1])
            for i in range(len(initial_individual[employee]) - 1)
        ]
        index_schedule = 0
        remaining_Tasks_of_employee = [
            task for task in remaining_Tasks if task.level <= employee.level
        ]
        while (
            index_schedule < len(scheldules_of_employee)
            and remaining_Tasks_of_employee != []
        ):
            next_fixed_task = scheldules_of_employee[index_schedule][1]
            while is_schedule_feasible(individual, employee, Tasks, Employees, Lunch):
                for task in individual[employee][1:]:
                    try:
                        remaining_Tasks.remove(task)
                        remaining_Tasks_of_employee.remove(task)
                    except ValueError:
                        continue
                if remaining_Tasks_of_employee == []:
                    break
                previous_task = individual[employee][-1]
                if previous_task.type != TaskType.BREAK:
                    previous_task_index = int(str(previous_task.id).strip("T")) - 1
                    weights = [
                        1 / (distance_matrix[previous_task_index][j] ** 3 + 1)
                        for j in range(len(remaining_Tasks_of_employee))
                    ]
                else:
                    Lunch = True
                    weights = [
                        1 / (travel_time(previous_task, task) ** 3 + 1)
                        for task in remaining_Tasks_of_employee
                    ]
                next_task = rd.choices(remaining_Tasks_of_employee, weights=weights)[0]
                individual[employee].append(next_task)

            else:
                if (
                    individual[employee][-1].type == TaskType.UNAVAILABILITIES
                    or individual[employee][-1].type == TaskType.ARRIVALS
                ):
                    index_schedule += 1
                    continue
                if remaining_Tasks_of_employee == []:
                    index_schedule += 1
        if remaining_Tasks_of_employee == []:
            is_doing_unavailability = not is_unavailability_done(individual[employee])
            unavailability = find_unavailabilty(employee, Tasks, Employees)
            if Lunch and is_doing_unavailability:
                if unavailability != []:
                    if unavailability.starting_time + unavailability.duration > 13 * 60:
                        append_break_task(
                            Tasks, employee.name, individual[employee], Employees
                        )
                        append_task(individual[employee], unavailability)
                    else:
                        append_task(individual[employee], unavailability)
                        append_break_task(
                            Tasks, employee.name, individual[employee], Employees
                        )
            elif Lunch:
                append_break_task(Tasks, employee.name, individual[employee], Employees)
            elif is_doing_unavailability:
                if unavailability != []:
                    append_task(individual[employee], unavailability)
            home = find_home(employee, Tasks, Employees)
            last_task = individual[employee][-1]
            if not home in individual[employee]:
                home.starting_time = (
                    last_task.starting_time
                    + last_task.duration
                    + travel_time(home, last_task)
                )
                individual[employee].append(home)

    return individual, remaining_Tasks


def create_population(Tasks, initial_population_number, Employees):

    population = []
    remaining_tasks_of_population = []
    for i in range(initial_population_number):
        individual = create_individual(copy.deepcopy(Tasks), Employees)
        population.append(individual[0])
        remaining_tasks_of_population.append(individual[1])
    return population, remaining_tasks_of_population


def calculate_objective(individual, alpha):
    task_duration_total = 0
    travel_time_total = 0

    for task_list in individual.values():
        for i in range(len(task_list)):
            if task_list[i].type == TaskType.NORMAL:
                task_duration_total += task_list[i].duration

    for task_list in individual.values():
        for i in range(len(task_list) - 1):
            travel_time_total += travel_time(task_list[i], task_list[i + 1])
    
    return (
        (1 - alpha) * task_duration_total - alpha * travel_time_total,
        task_duration_total,
        travel_time_total,
    )


def create_map_of_employees(individual):
    map_of_employees = []
    for employee, task_list in individual.items():
        map_of_employee_k = []
        map_of_employee_k.append((employee.longitude, employee.latitude, -1))
        for task in task_list:
            if task.type == TaskType.NORMAL:
                map_of_employee_k.append(
                    (
                        task.longitude,
                        task.latitude,
                        task.id,
                    )
                )
            if task.type == TaskType.UNAVAILABILITIES:
                map_of_employee_k.append(
                    (
                        task.longitude,
                        task.latitude,
                        "U",
                    )
                )
            if task.type == TaskType.BREAK:
                map_of_employee_k.append(
                    (
                        task.longitude,
                        task.latitude,
                        "B",
                    )
                )
        map_of_employee_k.append((employee.longitude, employee.latitude, -1))
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
    return map_of_employees


def create_travel_time_dict(individual):
    employee_travel_time = {employee.name: [] for employee in individual.keys()}
    for employee in individual.keys():
        Tasks = individual[employee]
        for i in range(len(Tasks) - 1):
            employee_travel_time[employee.name].append(
                (
                    Tasks[i].starting_time + Tasks[i].duration,
                    Tasks[i].starting_time
                    + Tasks[i].duration
                    + travel_time(Tasks[i], Tasks[i + 1]),
                )
            )
    return employee_travel_time


def clean_up_population(population, Tasks, Employees):
    i = 0
    while i < len(population):
        individual = population[i]
        is_individual_acceptable = True
        for employee in individual.keys():
            if not is_solution_acceptable(
                individual[employee], employee, Tasks, Employees
            ):
                is_individual_acceptable = False
                break
        if not is_individual_acceptable:
            population.pop(i)
        else:
            i += 1

    return population


def is_solution_acceptable(tasks, employee, Tasks, Employees):
    break_task = 0
    unavailability_task = 0
    return_home_task = 0
    if tasks[-1].type != TaskType.ARRIVALS:
        return False
    elif tasks[-1].starting_time > employee.end_time:
        print(
            f"WARNING !!!!!!!!!!! You are violating your employee {employee.name}'s right to go back home"
        )
        return False
    for t in Tasks:
        if (
            t.type == TaskType.BREAK
            and get_employee_name_by_index(Employees, t.employee_id) == employee.name
        ):
            if not t.id in [task.id for task in tasks if task.type == TaskType.BREAK]:
                print(
                    f"WARNING !!!!!!!!!!! You have no break your employee {employee.name} is gonna explode"
                )
                return False
            break_task = [task for task in tasks if task.type == TaskType.BREAK][0]
            if break_task.starting_time < 12 * 60:
                return False
            if break_task.starting_time > 13 * 60:
                return False
            break
    for t in Tasks:
        if (
            t.type == TaskType.UNAVAILABILITIES
            and get_employee_name_by_index(Employees, t.employee_id) == employee.name
        ):
            unavailability_task = t
            if not t.id in [
                task.id for task in tasks if task.type == TaskType.UNAVAILABILITIES
            ]:
                print(
                    f"WARNING !!!!!!!!!!! You have no unavailability your employee {employee.name} is gonna explode"
                )
                return False
            break

    if unavailability_task != 0 and break_task != 0:
        dict_break_unavailability = {
            break_task.starting_time: break_task,
            unavailability_task.starting_time: unavailability_task,
        }
        starting_time = min(break_task.starting_time, unavailability_task.starting_time)
        ending_time = max(break_task.starting_time, unavailability_task.starting_time)
        start_task = dict_break_unavailability[starting_time]
        end_task = dict_break_unavailability[ending_time]
        if (
            starting_time + start_task.duration + travel_time(start_task, end_task)
            > end_task.starting_time
        ):
            print(
                f"WARNING !!!!!!!!!!! Your employee can't travel through time {employee.name}'"
            )
            return False

    return True
