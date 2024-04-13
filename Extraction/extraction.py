from datetime import datetime
from enum import Enum

import pandas as pd


class Employee:
    def __init__(self, name, latitude, longitude, level, start_time, end_time):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.level = level
        self.start_time = time_to_duration(start_time)
        self.end_time = time_to_duration(end_time)

    def __repr__(self):
        return f"Employee: {self.name}, Latitude: {self.latitude}, Longitude: {self.longitude}, Level: {self.level}, Start Time: {self.start_time}, End Time: {self.end_time}"


class Task:
    def __init__(
        self,
        id,
        latitude,
        longitude,
        duration,
        level,
        opening_time,
        starting_time,
        closing_time,
        availabilities,
        employee_id,
        type,
    ):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.duration = duration
        self.level = level
        self.opening_time = opening_time
        self.starting_time = starting_time
        self.closing_time = closing_time
        self.availabilities = availabilities
        self.employee_id = employee_id
        self.type = type

    def __repr__(self):
        return f"Task ID: {self.id}, Latitude: {self.latitude}, Longitude: {self.longitude}, Duration: {self.duration}, Level: {self.level}, Opening Time: {self.opening_time}, Starting Time: {self.starting_time}, Closing Time: {self.closing_time}, Availabilities: {self.availabilities}, Employee ID: {self.employee_id}, Type: {self.type}"


class TaskType(Enum):
    UNAVAILABILITIES = "Unavailabilities"
    DEPARTURES = "Departures"
    ARRIVALS = "Arrivals"
    NORMAL = "Normal"
    BREAK = "Break"


def read_excel_to_dict(file_path, phase1):
    xls = pd.ExcelFile(file_path)
    all_data = {}
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name)
        data = df.to_dict(orient="records")
        all_data[sheet_name] = data

    all_tasks = []
    for task in all_data["Tasks"]:
        all_tasks.append(
            Task(
                task["TaskId"],
                task["Latitude"],
                task["Longitude"],
                task["TaskDuration"],
                task["Level"],
                time_to_duration(task["OpeningTime"]),
                0,
                time_to_duration(task["ClosingTime"]),
                [],
                None,
                TaskType.NORMAL,
            )
        )

    num_tasks = len(all_data["Tasks"])

    for unavailability in all_data["Employees Unavailabilities"]:
        num_tasks += 1
        employee_id = find_employee_index(
            all_data["Employees"], unavailability["EmployeeName"]
        )

        all_tasks.append(
            Task(
                f"T{num_tasks}",
                unavailability["Latitude"],
                unavailability["Longitude"],
                time_to_duration(unavailability["End"])
                - time_to_duration(unavailability["Start"]),
                0,
                time_to_duration(unavailability["Start"]),
                time_to_duration(unavailability["Start"]),
                time_to_duration(unavailability["End"]),
                [],
                employee_id,
                TaskType.UNAVAILABILITIES,
            )
        )

    employees = []
    for employee in all_data["Employees"]:
        num_tasks += 1
        employee_id = find_employee_index(
            all_data["Employees"], employee["EmployeeName"]
        )
        employees.append(
            Employee(
                employee["EmployeeName"],
                employee["Latitude"],
                employee["Longitude"],
                employee["Level"],
                employee["WorkingStartTime"],
                employee["WorkingEndTime"],
            )
        )
        all_tasks.append(
            Task(
                f"T{num_tasks}",
                employee["Latitude"],
                employee["Longitude"],
                0,
                0,
                time_to_duration(employee["WorkingStartTime"]),
                time_to_duration(employee["WorkingStartTime"]),
                time_to_duration(employee["WorkingEndTime"]),
                [],
                employee_id,
                TaskType.DEPARTURES,
            )
        )

    for employee in all_data["Employees"]:
        num_tasks += 1
        employee_id = find_employee_index(
            all_data["Employees"], employee["EmployeeName"]
        )
        all_tasks.append(
            Task(
                f"T{num_tasks}",
                employee["Latitude"],
                employee["Longitude"],
                0,
                0,
                time_to_duration(employee["WorkingStartTime"]),
                time_to_duration(employee["WorkingEndTime"]),
                time_to_duration(employee["WorkingEndTime"]),
                [],
                employee_id,
                TaskType.ARRIVALS,
            )
        )
        
    if not phase1:
        for employee in all_data["Employees"]:
            num_tasks += 1
            employee_id = find_employee_index(
                all_data["Employees"], employee["EmployeeName"]
            )
            all_tasks.append(
                Task(
                    f"T{num_tasks}",
                    None,
                    None,
                    60,
                    0,
                    12 * 60,
                    0,
                    14 * 60,
                    [],
                    employee_id,
                    TaskType.BREAK,
                )
            )

    task_unavailabilities = {}

    for task in all_data["Tasks Unavailabilities"]:
        id = task["TaskId"]
        start_time = time_to_duration(task["Start"])
        end_time = time_to_duration(task["End"])
        
        if id not in task_unavailabilities:
            task_unavailabilities[id] = []
        
        task_unavailabilities[id].append((start_time, end_time))

    task_availabilities = []  

    for task in all_tasks:
        opening_time = task.opening_time
        closing_time = task.closing_time
        if task.id in task_unavailabilities :
            availabilities = calculate_availabilities(opening_time, closing_time, task_unavailabilities[task.id])
        else:
            availabilities = [(opening_time, closing_time)]
        task.availabilities = availabilities
        task_availabilities.append(availabilities)
        
    return all_tasks, employees, task_availabilities


def time_to_duration(time_str):
    parsed_time = datetime.strptime(time_str, "%I:%M%p")
    reference_time = parsed_time.replace(hour=0, minute=0, second=0)

    time_difference = parsed_time - reference_time

    duration_in_minutes = time_difference.total_seconds() / 60

    return int(duration_in_minutes)


def find_employee_index(employees, employee_name):
    for index, employee in enumerate(employees):
        if employee["EmployeeName"] == employee_name:
            return index
    return -1

def calculate_availabilities(opening_time, closing_time, unavailabilities):
    availabilities = []

    if unavailabilities and closing_time < unavailabilities[0][0]:
        availabilities.append((opening_time, closing_time))
        return availabilities
    
    if unavailabilities and opening_time < unavailabilities[0][0]:
        availabilities.append((opening_time, unavailabilities[0][0]))

    for i in range(len(unavailabilities) - 1):
        gap_start = unavailabilities[i][1]
        gap_end = unavailabilities[i + 1][0]
        if gap_start < gap_end:
            availabilities.append((gap_start, gap_end))

    if unavailabilities and closing_time > unavailabilities[-1][1]:
        availabilities.append((unavailabilities[-1][1], closing_time))

    return availabilities
