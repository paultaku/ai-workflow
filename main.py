
import yaml
import os
import sys
from typing import List

# Ensure 'src' is importable when running this script directly.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from core.entity.task import Task

def print_project_info(describe):
    """Print project description information."""
    print(f"Project Name: {describe.get('name', 'N/A')}")
    if 'source' in describe:
        source = describe['source']
        print(f"Repository Type: {source.get('type', 'N/A')}")
        print(f"Repository URL: {source.get('repository', 'N/A')}")
        print(f"Version: {source.get('version', 'N/A')}")

def print_tasks_from_entities(tasks: List[Task]):
    """Print all tasks using Task entities while keeping output identical to before."""
    print(f"Total {len(tasks)} tasks:\n")

    # Define the output mapping to match the previous printing format.
    task_fields = [
        ("UUID", lambda t: t.uuid),
        ("Name", lambda t: t.name),
        ("Description", lambda t: t.description or "N/A"),
        ("Docker Image", lambda t: t.docker_image or "N/A"),
        ("Commit ID", lambda t: t.commit_id or "N/A"),
        ("Dependency Task ID", lambda t: t.dependency_task_id or "N/A"),
        ("Status", lambda t: t.status.value if t.status else "N/A"),
    ]

    for i, task in enumerate(tasks, 1):
        print(f"Task {i}:")
        for label, getter in task_fields:
            print(f"  {label}: {getter(task)}")
        print()

def main():
    """Read demo.yaml file and print task information."""
    yaml_file_path = os.path.join("features", "demo-1.yaml")
    
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        print("=== AI Workflow Task List ===\n")
        
        if 'describe' in data:
            print_project_info(data['describe'])
            print("-" * 50)
        
        if 'tasks' in data:
            # Convert raw task dicts into Task entities for safer, clearer handling.
            task_entities = [Task.from_dict(item) for item in data['tasks'] or []]
            print_tasks_from_entities(task_entities)
        else:
            print("No task list found")
            
    except FileNotFoundError:
        print(f"Error: File not found {yaml_file_path}")
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
