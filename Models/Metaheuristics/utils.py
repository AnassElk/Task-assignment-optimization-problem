import math
import sys

import geopy.distance

sys.path.insert(0, "C:/Users/anass/Documents/ST-74_Decision_Brain")
from Extraction.extraction import TaskType, read_excel_to_dict


def travel_time(a, b):
    coords_1 = (a.latitude, a.longitude)
    coords_2 = (b.latitude, b.longitude)
    return math.ceil(((geopy.distance.geodesic(coords_1, coords_2).km) * 60 / 50))


# add feasibility randomized


def is_schedule_feasible(individual, employee, Tasks, Employees, Lunch):
    if len(individual[employee]) <= 1:
        return True
    
    last_task = individual[employee][-2]
    current_task = individual[employee][-1]
    
    if (
        current_task.type == TaskType.BREAK
        or current_task.type == TaskType.UNAVAILABILITIES
    ):
        return True

    current_time = (
        last_task.starting_time
        + last_task.duration
        + travel_time(last_task, current_task)
    )

    if should_add_unavailability_or_break(
        individual, employee, Tasks, Employees, Lunch, current_task, current_time
    ):
        return False

    if should_return_home(current_time, individual, employee, Tasks, Employees):
        return False

    if not is_time_in_task_availabilities(current_time, current_task, individual, employee):
        return False
    if (
        current_task.type != TaskType.BREAK
        or current_task.type != TaskType.UNAVAILABILITIES
    ):
        current_task.starting_time = current_time

    return True


def should_add_unavailability_or_break(
    individual, employee, Tasks, Employees, Lunch, current_task, current_time
):
    is_doing_lunch = not Lunch and not is_lunch_break_feasible(
        current_time, current_task
    )
    is_doing_unavailability = not is_unavailability_done(
        individual[employee]
    ) and not is_unavailability_feasible(
        current_time, individual[employee], employee, Tasks, Employees
    )

    unavailability = find_unavailabilty(employee, Tasks, Employees)
    if is_doing_lunch and is_doing_unavailability:
        if unavailability != []:
            if unavailability.starting_time + unavailability.duration > 13 * 60:
                append_break_task(Tasks, employee.name, individual[employee], Employees)
                return True
            else:
                append_task(individual[employee], unavailability)
                return True
    elif is_doing_lunch:
        append_break_task(Tasks, employee.name, individual[employee], Employees)
        return True
    elif is_doing_unavailability:
        if unavailability != []:
            append_task(individual[employee], unavailability)
            return True
    return False

def find_home(employee, Tasks, Employees):
    home = 0
    for task in Tasks:
        if (
            task.type == TaskType.ARRIVALS
            and get_employee_name_by_index(Employees, task.employee_id) == employee.name
        ):
            home = task
    return home


def is_unavailability_done(current_tasks):
    for t in current_tasks:
        if t.type == TaskType.UNAVAILABILITIES:
            return True
    return False


def has_required_skill(employee, current_task):
    return employee.level >= current_task.level


def is_time_in_task_availabilities(current_time, current_task, individual, employee):
    is_doable = False
    for slots in current_task.availabilities:
        if (
            current_time >= slots[0]
            and current_time + current_task.duration <= slots[1]
        ):
            is_doable = True
    if not is_doable: 
        individual[employee].pop()
    return is_doable


def append_break_task(Tasks, employee_name, current_tasks, Employees):
    last_task = current_tasks[-2]
    
    for task in Tasks:
        if (
            task.type == TaskType.BREAK
            and get_employee_name_by_index(Employees, task.employee_id) == employee_name
        ):
            task.starting_time = max(
                last_task.starting_time + last_task.duration, 12 * 60
            )
            task.longitude = last_task.longitude
            task.latitude = last_task.latitude
            append_task(current_tasks, task)
            break


def is_unavailability_feasible(current_time, current_tasks, employee, Tasks, Employees):
    unavailability = find_unavailabilty(employee, Tasks, Employees)
    if unavailability == []:
        return True
    elif (
        current_time
        + current_tasks[-1].duration
        + travel_time(current_tasks[-1], unavailability)
        > unavailability.starting_time
    ):
        return False
    else:
        return True


def should_return_home(current_time, individual, employee, Tasks, Employees):
    last_task = individual[employee][-2]
    current_task = individual[employee][-1]
    if (
        current_time + current_task.duration + travel_time(current_task, employee)
        > employee.end_time
    ):
        home_task = find_home(employee, Tasks, Employees)
            
        home_task.starting_time = (
            last_task.starting_time
            + last_task.duration
            + travel_time(last_task, employee)
        )
        append_task(individual[employee], home_task)
        return True

    return False


def append_task(current_tasks, task):
    current_tasks.pop()
    current_tasks.append(task)


def find_unavailabilty(employee, Tasks, Employees):
    unavailability = []
    for task in Tasks:
        if (
            task.type == TaskType.UNAVAILABILITIES
            and get_employee_name_by_index(Employees, task.employee_id) == employee.name
        ):
            unavailability = task
            break
    return unavailability


def find_break(employee, Tasks, Employees):
    for task in Tasks:
        if (
            task.type == TaskType.BREAK
            and get_employee_name_by_index(Employees, task.employee_id) == employee.name
        ):
            return task


def is_lunch_break_feasible(current_time, current_task):
    return current_time + current_task.duration <= 13 * 60


def is_lunch_break_feasible_after_current_task(current_time, current_task):
    lunch_feasible = (
        current_time + current_task.duration >= 13 * 60
        and current_time + current_task.duration <= 12 * 60
    )
    return lunch_feasible, current_time + current_task.duration


def get_employee_name_by_index(Employees, index):
    for i in range(len(Employees) + 1):
        if i == index:
            return Employees[i].name
