import bisect
import copy
import random
import sys

import numpy as np

sys.path.insert(0, "C:/Users/anass/Documents/ST-74_Decision_Brain")

from Extraction.extraction import Employee, Task, TaskType, read_excel_to_dict
from Models.Metaheuristics.initialization import create_individual
from Models.phase1 import time_to_duration, travel_time


class MutationTracker:
    def __init__(self):
        self.mutation_counts = {'insert': 0, 'swap': 0, 'remove': 0, 'reposition': 0}
        self.successful_mutations = {'insert': 0, 'swap': 0, 'remove': 0, 'reposition': 0}

    def insert(self):
        self.mutation_counts['insert'] += 1

    def insert_successful(self):
        self.successful_mutations['insert'] += 1

    def swap(self):
        self.mutation_counts['swap'] += 1

    def swap_successful(self):
        self.successful_mutations['swap'] += 1

    def remove(self):
        self.mutation_counts['remove'] += 1

    def remove_successful(self):
        self.successful_mutations['remove'] += 1

    def reposition(self):
        self.mutation_counts['reposition'] += 1

    def reposition_successful(self):
        self.successful_mutations['reposition'] += 1

    def get_mutation_counts(self):
        return self.mutation_counts

    def get_successful_mutations(self):
        return self.successful_mutations
    
    def calculate_total_counts(self):
        total_counts = sum(self.mutation_counts.values())
        total_successful_counts = sum(self.successful_mutations.values())
        return total_counts, total_successful_counts
    
    def __repr__(self):
        mutation_info = ", ".join([f"{mutation} {self.mutation_counts[mutation]}" for mutation in self.mutation_counts])
        successful_mutation_info = ", ".join([f"{mutation} successful {self.successful_mutations[mutation]}" for mutation in self.successful_mutations])
        return f"Mutations: {mutation_info}, {successful_mutation_info}"

#Task Insertion
def insert_task(individual, undone_tasks, chosen_employees, tracker):
    for employee in chosen_employees:
        if employee in individual:
            tasks = individual[employee]
            tasks_doable_level = [
                task for task in undone_tasks if task.level <= employee.level
            ]
            if tasks_doable_level:
                selected_tasks = pick_undone_task(tasks, tasks_doable_level, 1)
                if selected_tasks:
                    for selected_task in selected_tasks:
                        index_to_insert = bisect.bisect_left(
                            [task.starting_time for task in tasks],
                            selected_task.starting_time,
                        )
                        tasks.insert(index_to_insert, selected_task)
                        individual[employee] = tasks
                        undone_tasks.remove(selected_task)
                        tracker.insert_successful()
        return individual


# Task Swapping within an Employee's Task List
def swap_task(individual, chosen_employees, tracker):
    for employee in chosen_employees:
        if employee in individual:
            tasks = individual[employee]
            if len(tasks) > 1:
                selected_tasks = pick_task(tasks, 2)
                if len(selected_tasks) > 1 and is_swap_feasible(
                    tasks, selected_tasks[0], selected_tasks[1]
                ):
                    swapPositions(tasks, selected_tasks[0], selected_tasks[1])
                    individual[employee] = tasks
                    tracker.swap_successful()
    return individual


def swapPositions(list, e1, e2):
    index1 = list.index(e1)
    index2 = list.index(e2)
    list[index1], list[index2] = list[index2], list[index1]
    return list

# Task Repositioning between Employees
def reposition_task(individual, chosen_employees, tracker):
    both_tasks = []
    both_employees = []
    for employee in chosen_employees:
        if employee in individual:
            both_employees.append(employee)
            all_tasks = individual[employee]
            if len(all_tasks) > 1:
                selected_task = pick_task_based_level(all_tasks, 1, employee.level)
                if not selected_task:
                    return individual
                both_tasks.append(
                    selected_task[0]
                )
    if len(both_tasks) == 2:
        ok1, st1 = can_insert_between_two_tasks(
            both_tasks[0],
            individual[both_employees[1]][find_task_index_by_id(individual[both_employees[1]], both_tasks[1].id) - 1],
            individual[both_employees[1]][find_task_index_by_id(individual[both_employees[1]], both_tasks[1].id) + 1],
            None,
            ""
        )
        
        ok2, st2 = can_insert_between_two_tasks(
            both_tasks[1],
            individual[both_employees[0]][find_task_index_by_id(individual[both_employees[0]], both_tasks[0].id) - 1],
            individual[both_employees[0]][find_task_index_by_id(individual[both_employees[0]], both_tasks[0].id) + 1],
            None,
            ""
        )
        if ok1 and ok2:
            both_tasks[0].starting_time = st1.starting_time
            both_tasks[1].starting_time = st2.starting_time
            index_task1 = find_task_index_by_id(
                individual[both_employees[0]], both_tasks[0].id
            )
            index_task2 = find_task_index_by_id(
                individual[both_employees[1]], both_tasks[1].id
            )
            individual[both_employees[0]].remove(both_tasks[0])
            individual[both_employees[1]].remove(both_tasks[1])
            individual[both_employees[0]].insert(index_task1, both_tasks[1])
            individual[both_employees[1]].insert(index_task2, both_tasks[0])
            tracker.reposition_successful()
    return individual


# Task Removal by Priority
def remove_task(individual, chosen_employees, tracker):
    for employee in chosen_employees:
        if employee in individual:
            all_tasks = individual[employee]
            normal_tasks = [task for task in all_tasks if task.type == TaskType.NORMAL]
            if len(normal_tasks) != 0:
                ratio_travel_times = {}
                for i in range(1, len(all_tasks)):
                    if all_tasks[i].type == TaskType.NORMAL:
                        travel_time_prev_task = travel_time(
                            all_tasks[i - 1], all_tasks[i]
                        )
                        travel_time_next_task = travel_time(
                            all_tasks[i], all_tasks[i + 1]
                        )
                        initial_travel_time_total = (
                            travel_time_prev_task + travel_time_next_task
                        )
                        updated_travel_time = travel_time(
                            all_tasks[i - 1], all_tasks[i + 1]
                        )
                        ratio_travel_times[all_tasks[i]] = (
                            updated_travel_time / initial_travel_time_total
                        )

                selected_tasks = select_items_without_duplicates(list(ratio_travel_times.keys()), 1, list(ratio_travel_times.values()))
                if selected_tasks:
                    selected_task = selected_tasks[0]
                else:
                    print("No task could be selected.")
                    continue

                for tasks in individual.values():
                    if selected_task in tasks:
                        tasks.remove(selected_task)
                        tracker.remove_successful()
                        break

    return individual    
    
def mutate(individual, undone_tasks, mutationRate, tracker):
    if np.random.rand() < mutationRate:
        mutationType = random.randint(0, 3)
        if mutationType == 0:
            # Task Insertion
            tracker.insert()
            chosen_employees = choose_employee(
                individual, random.randint(1, len(individual))
            )
            individual = insert_task(individual, undone_tasks, chosen_employees, tracker)
        elif mutationType == 1:
            # Task Swapping within an Employee's Task List
            tracker.swap()
            chosen_employees = choose_employee(
                individual, random.randint(1, len(individual))
            )
            individual = swap_task(individual, chosen_employees, tracker)
        elif mutationType == 2:
            # Task Repositioning between Employees
            tracker.reposition()
            chosen_employees = choose_employee(individual, 2)
            individual = reposition_task(individual, chosen_employees, tracker)
        else:
            # Task Removal by Priority
            tracker.remove()
            chosen_employees = choose_employee(
                individual, random.randint(1, len(individual))
            )
            individual = remove_task(individual, chosen_employees, tracker)
    return individual


def choose_employee(individual, num_workers_to_pick):
    if num_workers_to_pick >= len(individual):
        return list(individual.keys())

    total_tasks = sum(len(tasks) for tasks in individual.values())

    weights = {
        employee: len(tasks) / total_tasks for employee, tasks in individual.items()
    }

    chosen_employees = select_items_without_duplicates(list(individual.keys()), num_workers_to_pick, list(weights.values()))

    return chosen_employees


def select_items_without_duplicates(items, num_items_to_pick, weights):
    selected_items = []
    remaining_items = items[:]

    try:
        for _ in range(num_items_to_pick):

            valid_items = [item for item, weight in zip(remaining_items, weights) if weight > 0]
            valid_weights = [weight for weight in weights if weight > 0]

            if len(valid_items) != len(valid_weights):
                raise ValueError('The number of weights does not match the population')
            
            if not valid_items:
                break

            item = random.choices(valid_items, weights=valid_weights)[0]
            selected_items.append(item)
            remaining_items.remove(item)

    except ValueError as e:
        print(e)

    return selected_items


def pick_task(tasks, num_tasks_to_pick):
    if not tasks:
        return []

    normal_tasks = [task for task in tasks if task.type == TaskType.NORMAL]
    if len(normal_tasks) <= num_tasks_to_pick:
        return normal_tasks

    weights = []
    for i, task in enumerate(normal_tasks):
        previous_task = tasks[find_task_index_by_id(tasks, task.id) - 1]
        next_task = tasks[find_task_index_by_id(tasks, task.id) + 1]
        if previous_task.type == TaskType.BREAK:
            weight = travel_time(
                tasks[find_task_index_by_id(tasks, task.id) - 2], task
            ) + travel_time(task, next_task)
        elif next_task.type == TaskType.BREAK:
            weight = travel_time(previous_task, task) + travel_time(
                task, tasks[find_task_index_by_id(tasks, task.id) + 2]
            )
        else:
            weight = travel_time(previous_task, task) + travel_time(task, next_task)
        weights.append(weight)

    selected_tasks = select_items_without_duplicates(
        normal_tasks, num_tasks_to_pick, weights=weights
    )

    return selected_tasks


def pick_task_based_level(tasks, num_tasks_to_pick, level):
    if not tasks:
        return []

    normal_tasks = [
        task for task in tasks if task.type == TaskType.NORMAL and task.level <= level
    ]
    if not normal_tasks:
        return[]
    
    if len(normal_tasks) <= num_tasks_to_pick:
        return normal_tasks

    weights = []
    for task in normal_tasks:
        previous_task = tasks[find_task_index_by_id(tasks, task.id) - 1]
        next_task = tasks[find_task_index_by_id(tasks, task.id) + 1]
        if previous_task.type == TaskType.BREAK:
            weight = travel_time(
                tasks[find_task_index_by_id(tasks, task.id) - 2], task
            ) + travel_time(task, next_task)
        elif next_task.type == TaskType.BREAK:
            weight = travel_time(previous_task, task) + travel_time(
                task, tasks[find_task_index_by_id(tasks, task.id) + 2]
            )
        else:
            weight = travel_time(previous_task, task) + travel_time(task, next_task)
        weights.append(weight)

    selected_tasks = select_items_without_duplicates(
        normal_tasks, num_tasks_to_pick, weights=weights
    )
    return selected_tasks


def is_swap_feasible(tasks, task1, task2):
    index_task1 = find_task_index_by_id(tasks, task1.id)
    index_task2 = find_task_index_by_id(tasks, task2.id)
    ok, st1 = can_insert_between_two_tasks(
        task1, tasks[index_task2 - 1], tasks[index_task2 + 1], task2, ""
    )
    if ok:
        if index_task1 > index_task2:
            ok2, st2 = can_insert_between_two_tasks(
                task2, tasks[index_task1 - 1], tasks[index_task1 + 1], st1, "smaller"
            )
        else:
            ok2, st2 = can_insert_between_two_tasks(
                task2, tasks[index_task1 - 1], tasks[index_task1 + 1], st1, "bigger"
            )
    else:
        return False
    if ok and ok2:
        task1.starting_time = st1.starting_time
        task2.starting_time = st2.starting_time

        return True
    return False


def find_task_index_by_id(tasks, id):
    for i, t in enumerate(tasks):
        if t.id == id:
            return i
    return -1


def pick_undone_task(tasks, tasks_undone, num_tasks_to_pick):
    if not tasks:
        return []

    num_tasks_to_pick = min(num_tasks_to_pick, len(tasks_undone))

    selected_tasks = []
    weights = []
    for task_undone in tasks_undone:
        can_insert, total_travel_time = can_insert_task(task_undone, tasks)
        if can_insert:
            selected_tasks.append(task_undone)
            weights.append(total_travel_time)

    if selected_tasks:
        return select_items_without_duplicates(selected_tasks, num_tasks_to_pick, weights=weights)
    else:
        return []


def can_insert_between_two_tasks(task_to_insert, task2, task1, other_task, comparaison):
    if comparaison == "smaller":
        prev_task_end_time = other_task.starting_time + other_task.duration
    else:
        prev_task_end_time = task2.starting_time + task2.duration
    if task_to_insert.id == task1.id:
        travel_time_prev_task = travel_time(task2, task_to_insert)
        travel_time_next_task = travel_time(task_to_insert, other_task)
    elif task_to_insert.id == task2.id:
        travel_time_prev_task = travel_time(other_task, task_to_insert)
        travel_time_next_task = travel_time(task_to_insert, task1)
    else:
        travel_time_prev_task = travel_time(task2, task_to_insert)
        travel_time_next_task = travel_time(task_to_insert, task1)
    if comparaison == "bigger":
        next_task_starting_time = other_task.starting_time
    else:
        next_task_starting_time = task1.starting_time
    if (
        next_task_starting_time
        - travel_time_next_task
        - prev_task_end_time
        - travel_time_prev_task
        >= task_to_insert.duration
    ):
        task_to_insert_copy = copy.deepcopy(task_to_insert)
        task_to_insert_copy.starting_time = prev_task_end_time + travel_time_prev_task
        if is_task_available(task_to_insert_copy):
            return True, task_to_insert_copy

    return False, None


def is_task1_before_task2(tasks, task1, task2):
    index_task1 = find_task_index_by_id(tasks, task1.id)
    index_task2 = find_task_index_by_id(tasks, task2.id)
    if index_task1 == index_task2 - 1:
        return True
    return False


def is_task1_after_task2(tasks, task1, task2):
    index_task1 = find_task_index_by_id(tasks, task1.id)
    index_task2 = find_task_index_by_id(tasks, task2.id)
    if index_task1 == index_task2 + 1:
        return True
    return False


def can_insert_task(task_to_insert, tasks):
    for i in range(1, len(tasks)):
        # Insert a task between two tasks that aren't a break
        prev_task_end_time = tasks[i - 1].starting_time + tasks[i - 1].duration
        travel_time_prev_task = travel_time(tasks[i - 1], task_to_insert)
        travel_time_next_task = travel_time(task_to_insert, tasks[i])
        if (
            tasks[i].starting_time
            - travel_time_next_task
            - prev_task_end_time
            - travel_time_prev_task
            >= task_to_insert.duration
        ):
            task_to_insert.starting_time = (
                prev_task_end_time + travel_time_prev_task
            )
            if is_task_available(task_to_insert):
                total_travel_time = travel_time_prev_task + travel_time_next_task
                return True, total_travel_time
    return False, None


def is_task_available(task):
    if (
        task.starting_time < task.opening_time
        or task.starting_time + task.duration > task.closing_time
    ):
        return False
    for availibilty in task.availabilities:
        if (
            task.starting_time >= availibilty[0]
            and task.starting_time + task.duration <= availibilty[1]
        ):
            return True