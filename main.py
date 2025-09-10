import yaml
import os

def print_project_info(describe):
    """Print project description information."""
    print(f"Project Name: {describe.get('name', 'N/A')}")
    if 'source' in describe:
        source = describe['source']
        print(f"Repository Type: {source.get('type', 'N/A')}")
        print(f"Repository URL: {source.get('repository', 'N/A')}")
        print(f"Version: {source.get('version', 'N/A')}")

def print_tasks(tasks):
    """Print all tasks with their details."""
    print(f"Total {len(tasks)} tasks:\n")
    
    task_fields = [
        ('UUID', 'uuid'),
        ('Name', 'Name'),
        ('Description', 'Prompt'),
        ('Docker Image', 'DockerImage'),
        ('Commit ID', 'CommitID'),
        ('Dependency Task ID', 'DependencyTaskID'),
        ('Status', 'Status')
    ]
    
    for i, task in enumerate(tasks, 1):
        print(f"Task {i}:")
        for label, field in task_fields:
            print(f"  {label}: {task.get(field, 'N/A')}")
        print()

def main():
    """Read demo.yaml file and print task information."""
    yaml_file_path = os.path.join("features", "demo.yaml")
    
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        print("=== AI Workflow Task List ===\n")
        
        if 'describe' in data:
            print_project_info(data['describe'])
            print("-" * 50)
        
        if 'tasks' in data:
            print_tasks(data['tasks'])
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
