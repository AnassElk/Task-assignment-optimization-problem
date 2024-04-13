import sys
import time

import matplotlib.pyplot as plt
from initialization import (calculate_objective, clean_up_population,
                            create_map_of_employees, create_population,
                            create_travel_time_dict)

from Extraction.extraction import read_excel_to_dict

sys.path.insert(0, "C:/Users/anass/Documents/ST-74_Decision_Brain/Models")
from Metaheuristics.mutation import MutationTracker, mutate
from output import (generate_plot_gantt_diagram,
                    generate_plot_map_of_employees,
                    generate_plot_map_of_employees_with_arrows,
                    generate_solution_file_phase3)


def generate_gantt_diagram(Tasks, individual):
    employee_travel_time = create_travel_time_dict(individual)
    employee_tasks = {
        employee.name: [
            (
                int(str(individual[employee][i].id).strip("T")) - 1,
                individual[employee][i].starting_time,
                individual[employee][i].duration,
                0,
                0
            )
            for i in range(len(individual[employee]))
        ]
        for employee in individual.keys()
    }

    generate_plot_gantt_diagram(employee_tasks, employee_travel_time, Tasks)
def plot_obj_solution_progression(population, objective_list):
    x = [i for i in range(len(population))]
    objective_list.reverse()
    plt.plot(x, objective_list, label="Population Size Impact on Objective Function")
    plt.ylabel("objective function")
    plt.xlabel("number of itterations")
    plt.legend()
    plt.show()


def run_model(initial_population_number, instance_file_name, mutation_rate, alpha):
    Tasks, Employees, task_availabilities = read_excel_to_dict(
        instance_file_name, False
    )
    start_time = time.time()
    population, remaining_tasks_of_population = create_population(Tasks, initial_population_number, Employees)

    print_best_individual(population, alpha)
    
    print(
        f"-------------------WE GOT THE SOLUTION IN {(time.time()-start_time)//60} Minutes:{(time.time()-start_time)%60} Seconds--------------------------"
    )
    
    end_time = time.time()
    tracker = MutationTracker()
    for i in range(len(population)):
        mutate(population[i], remaining_tasks_of_population[i], mutation_rate, tracker)
    print("\n-----------------------TRACKER-----------------------------")
    print(tracker)
    print_best_individual(population, alpha)
    print("\n")
    
    print(
        f"-------------------WE GOT THE SOLUTION MUTATED IN {(time.time()-end_time)//60} Minutes:{(time.time()-end_time)%60} Seconds--------------------------"
    )
    end_time = time.time()
    population = clean_up_population(population, Tasks, Employees)
    print_best_individual(population, alpha)
    
    print(
        f"-------------------WE GOT THE SOLUTION CLEANED IN {(time.time()-end_time)//60} Minutes:{(time.time()-end_time)%60} Seconds--------------------------"
    )
    print("new_population_size", len(population))
    
    objective_list = []
    for individual in population:
        objective_list.append(calculate_objective(individual, 0.5)[0])

    dict_order = {objective_list[index]: index for index in range(len(population))}
    objective_list.sort(reverse=True)
    best_index = 0

    print_best_individual(population, alpha)

    individual = population[dict_order[objective_list[best_index]]]
    map_of_employees = create_map_of_employees(
        population[dict_order[objective_list[best_index]]]
    )

    generate_plot_map_of_employees_with_arrows(Tasks, map_of_employees)
    generate_plot_map_of_employees(Employees, map_of_employees)
    generate_gantt_diagram(Tasks, individual)
    generate_solution_file_phase3("solution_file_phase3.txt", individual, Tasks)
    plot_obj_solution_progression(population, objective_list)


def print_best_individual(population, alpha, best_index = 0):
    objective_list = []
    for individual in population:
        objective_list.append(calculate_objective(individual, alpha)[0])

    dict_order = {objective_list[i]: i for i in range(len(population))}
    objective_list.sort(reverse=True)
    
    obj = calculate_objective(
        population[dict_order[objective_list[best_index]]], alpha
    )
    print(f"\ntask_duration, travel_time {(obj[1], obj[2])} \n")
    

if __name__ == "__main__":
    run_model(10, "Instances/InstanceAustraliaV2.xlsx", 0.7, 0.3)
