import math
import sys

import folium
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from folium.plugins import AntPath
from gurobipy import *
from matplotlib.patches import FancyArrowPatch

sys.path.insert(0, "C:/Users/yassi/Desktop/projet ST7/ST-74_Decision_Brain")
from Extraction.extraction import TaskType

task_url = "https://cdn-icons-png.flaticon.com/512/4345/4345573.png"
home_url = "https://cdn.icon-icons.com/icons2/2248/PNG/512/home_circle_icon_137496.png"
unavailability_icon = "https://cdn-icons-png.flaticon.com/512/8373/8373460.png"
break_icon = "https://cdn-icons-png.flaticon.com/512/7976/7976343.png"
colors = ["red", "blue", "green", "purple", "grey"]*10

def get_employee_name_by_index(Employees, index):
    for i in range(len(Employees) + 1):
        if i == index:
            return Employees[i].name

def create_icon_from_url(icon_url):
    icon = folium.CustomIcon(icon_url, icon_size=(48, 48), icon_anchor=(12, 12))
    return icon


def generate_plot_map_of_employee_with_arrows(j, map, locations, Tasks):
    for i, loc in enumerate(locations[:-1]):

        if loc[2] == "U":
            folium.Marker(
                [loc[1], loc[0]],
                popup=loc[2],
                icon=create_icon_from_url(unavailability_icon),
            ).add_to(map)
        elif loc[2] == "B":
            folium.Marker(
                [loc[1], loc[0]], popup=loc[2], icon=create_icon_from_url(break_icon)
            ).add_to(map)
        elif loc[2] == -1:
            folium.Marker(
                [loc[1], loc[0]],
                popup=loc[2],
                icon=create_icon_from_url(home_url),
            ).add_to(map)
        else:
            folium.Marker(
                [loc[1], loc[0]], popup=loc[2], icon=create_icon_from_url(task_url)
            ).add_to(map)

    for i in range(len(locations) - 1):
        start_pos = [locations[i][1], locations[i][0]]
        end_pos = [locations[i + 1][1], locations[i + 1][0]]
        AntPath(locations=[start_pos, end_pos], color=colors[j]).add_to(map)


def generate_plot_map_of_employees_with_arrows(Tasks, map_of_employees):
    map = folium.Map(location=[51.9194, 19.1451], zoom_start=8)
    for j, locations_of_employee in enumerate(map_of_employees):
        generate_plot_map_of_employee_with_arrows(j, map, locations_of_employee, Tasks)
    map.save("map_with_arrows.html")


def generate_solution_file(x, t, Tasks, Employees, filename, phase1):
    with open(filename, "w") as f:
        f.write("taskId;performed;employeeName;startTime\n")
        num_employees = len(Employees)
        num_tasks = len(Tasks)
        lunch_breaks_indexes = []
        for i in range(num_tasks):
            
            if Tasks[i].type == TaskType.NORMAL:
                if quicksum(x[i, j, k1] for j in range(num_tasks) for k1 in range(num_employees)).getValue() == 0:
                    f.write(f"T{i+1};0;;;\n")
                    continue
                for k in range(num_employees):
                    if quicksum(x[i, j, k] for j in range(num_tasks)).getValue() == 1:
                        f.write(f"T{i+1};1;{Employees[k].name};{t[i].x};\n")
                    elif quicksum(x[i, j, k1] for j in range(num_tasks) for k1 in range(num_employees)).getValue() == 0:
                        f.write(f"T{i+1};0;;;\n")
            if not phase1:
                if Tasks[i].type == TaskType.BREAK:
                    lunch_breaks_indexes.append(i)
                
        if not phase1:
            f.write("\nemployeeName;lunchBreakStartTime;\n")
            for k in range(num_employees):
                f.write(f"{Employees[k].name};{t[lunch_breaks_indexes[k]].x};\n")

def generate_plot_map_of_employees(employees,map_of_employees):
    fig, ax = plt.subplots()
    for i, employee_path in enumerate(map_of_employees):
        x, y, z = zip(*employee_path)
        ax.scatter(x, y, s=150, zorder=1)
        for j in range(len(x)):
            if z[j] != -1:
                ax.text(
                    x[j],
                    y[j],
                    z[j],
                    fontsize=15,
                    ha="center",
                    va="center",
                    color="black",
                )
            elif z[j] == -1:
                ax.text(
                    x[j],
                    y[j],
                    "H {}".format(i + 1),
                    fontsize=15,
                    ha="center",
                    va="center",
                    color="red",
                )
            if j > 0:
                arrow = FancyArrowPatch(
                    (x[j - 1], y[j - 1]),
                    (x[j], y[j]),
                    arrowstyle="->",
                    mutation_scale=30,
                    color=f"C{i}",
                    shrinkA=10,
                    shrinkB=10,
                )
                ax.add_patch(arrow)
        ax.plot(x, y, "o-", label=f"{get_employee_name_by_index(employees,i)}", markersize=5, linewidth=1)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Map of Employee Movements with Task Order")
    ax.legend()
    plt.show()


def generate_plot_gantt_diagram(employee_tasks, employee_travel_time, Tasks):
    fig, ax = plt.subplots(figsize=(10, 4))

    task_colors = plt.cm.get_cmap(
        "tab20", sum(len(task_list) for task_list in employee_tasks.values())
    )

    current_color_index = 0
    min_time = float("inf")
    max_time = 0

    for employee, tasks in employee_tasks.items():
        for id, start_time, duration, lat, long  in tasks:
            end_time = start_time + duration
            color = task_colors(current_color_index)

            if Tasks[id].type == TaskType.ARRIVALS:
                label = f"A"
            elif Tasks[id].type == TaskType.DEPARTURES:
                label = f"D"
            elif Tasks[id].type == TaskType.UNAVAILABILITIES:
                label = f"U"
            elif Tasks[id].type == TaskType.BREAK:
                label = f"B"
            else:
                label = f"T{id +1}"

            ax.plot(
                [start_time, end_time],
                [employee, employee],
                color=color,
                linewidth=15,
                solid_capstyle="butt",
                label=label,
            )

            ax.text(
                (start_time + end_time) / 2,
                employee,
                label,
                ha="center",
                va="center",
                color="black",
                fontsize=8,
            )

            current_color_index += 1
            min_time = min(min_time, start_time)
            max_time = max(max_time, end_time)

    for employee, travel_times in employee_travel_time.items():
        for travel_time_start, start_time in travel_times:
            time_difference = start_time - travel_time_start
            if time_difference > 60:
                hours = int(time_difference / 60)
                minutes = int(time_difference % 60)
                time_display = f'{hours:02d}:{minutes:02d}'
            else:
                time_display = str(int(time_difference))
            y = list(employee_tasks.keys()).index(employee)
            ax.plot([travel_time_start, start_time], [y, y], color='red', linestyle='-', marker='|')
            ax.plot([travel_time_start, start_time], [y, y], color='red', linestyle='-', marker='|')
            ax.annotate(
                time_display,
                xy=((start_time + travel_time_start) / 2, y),
                ha='center',
                va='bottom',
                fontsize=6
            )

    ax.set_yticks(range(len(employee_tasks)))
    ax.set_yticklabels([f"{k}" for k in employee_tasks.keys()])
    ax.set_xlabel("Time (hh:mm)")
    ax.set_title("Gantt Chart of Task Assignments")
    ax.set_ylim(-0.1, len(employee_tasks) + 2)
    ax.set_xlim(
        math.floor(min_time / 60) * 60 - 30, math.floor((max_time + 60) / 60) * 60
    )

    ax.set_xticks(np.arange(min_time // 60 * 60, max_time // 60 * 60 + 61, 60))
    ax.set_xticklabels(
        [f"{int(tick // 60):02d}:{int(tick % 60):02d}" for tick in ax.get_xticks()]
    )

    mplcursors.cursor(hover=True).connect(
        "add",
        lambda sel: sel.annotation.set_text(
            f"Time: {int(sel.target[0] // 60):02d}:{int(sel.target[0] % 60):02d}"
        ),
    )

    plt.show()
    
def generate_solution_file_phase3( filename,individual,Tasks):
    tasks_dict = {task.id: {"employee":"","starting_time":0} for task in Tasks}

    with open(filename, "w") as f:
        f.write("taskId;performed;employeeName;startTime\n")
        for employee,task_list in individual.items():
                for task in task_list:
                    if task.type==TaskType.NORMAL :
                            tasks_dict[task.id]["employee"]=employee.name
                            tasks_dict[task.id]["starting_time"]=task.starting_time

        for task_id,infos in tasks_dict.items():
            if (infos["starting_time"]==0):
               f.write(f"{task_id};0;;;\n")
            else:
                f.write(f"{task_id};1;{infos['employee']};{infos['starting_time']};\n")

        f.write("\nemployeeName;lunchBreakStartTime;\n")
        for employee,task_list in individual.items():
           for task in task_list:
                if task.type==TaskType.BREAK :
                    f.write(f"{employee};{task.starting_time};\n")