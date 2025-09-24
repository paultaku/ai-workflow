#!/usr/bin/env python3
"""
Cursor CLI tool for AI workflow management.

This tool executes AI workflow tasks defined in YAML configuration files.
It supports concurrent task execution with comprehensive logging and error handling.

Usage:
    python src/local/cursor.py --path ./tasks.yaml
    python src/local/cursor.py --path ./tasks.yaml --verbose

Author: AI Workflow Team
Version: 1.0.0
"""

import argparse
import os
import sys
from pathlib import Path
import yaml
import subprocess
import concurrent.futures
import threading
import logging
from dataclasses import dataclass
from typing import Dict, Any, List



# =============================================================================
# CONFIGURATION AND SETUP
# =============================================================================

def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: If True, set logging level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TaskResult:
    """Result of a task execution."""
    task_uuid: str
    task_name: str
    success: bool
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    error_message: str = ""


# =============================================================================
# YAML FILE SYNCHRONIZATION FUNCTIONS
# =============================================================================

def sync_task_status_to_yaml(yaml_file_path: str, tasks: List[Dict[str, Any]]) -> None:
    """
    Synchronize task statuses back to the original YAML file.
    
    Args:
        yaml_file_path: Path to the original YAML file
        tasks: List of tasks with updated statuses
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Read the original YAML file
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)
        
        if not yaml_content or 'tasks' not in yaml_content:
            logger.warning(f"No tasks found in YAML file: {yaml_file_path}")
            return
        
        # Create a mapping of task names to updated statuses
        status_map = {task.get('name'): task.get('status') for task in tasks}
        
        # Update the YAML content with new statuses
        updated_count = 0
        for yaml_task in yaml_content['tasks']:
            task_name = yaml_task.get('Name') or yaml_task.get('name')
            if task_name in status_map:
                old_status = yaml_task.get('Status', yaml_task.get('status'))
                new_status = status_map[task_name]
                
                if old_status != new_status:
                    yaml_task['Status'] = new_status
                    updated_count += 1
                    logger.debug(f"Updated {task_name}: {old_status} → {new_status}")
        
        # Write the updated content back to the file
        with open(yaml_file_path, 'w', encoding='utf-8') as file:
            yaml.dump(yaml_content, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"✅ Synchronized {updated_count} task status(es) to {yaml_file_path}")
        
    except Exception as e:
        logger.error(f"❌ Failed to sync task statuses to YAML file: {e}")
        # Don't raise the exception to avoid breaking the main workflow

def sync_task_status_on_update(yaml_file_path: str, task_name: str, new_status: str, 
                              all_tasks: List[Dict[str, Any]]) -> None:
    """
    Sync a single task status update to the YAML file.
    
    Args:
        yaml_file_path: Path to the original YAML file
        task_name: Name of the task that was updated
        new_status: New status of the task
        all_tasks: List of all tasks (for context)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Read the original YAML file
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            yaml_content = yaml.safe_load(file)
        
        if not yaml_content or 'tasks' not in yaml_content:
            return
        
        # Find and update the specific task
        for yaml_task in yaml_content['tasks']:
            task_name_in_yaml = yaml_task.get('Name') or yaml_task.get('name')
            if task_name_in_yaml == task_name:
                old_status = yaml_task.get('Status', yaml_task.get('status'))
                yaml_task['Status'] = new_status
                
                # Write the updated content back to the file
                with open(yaml_file_path, 'w', encoding='utf-8') as file:
                    yaml.dump(yaml_content, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
                logger.debug(f"🔄 Synced {task_name}: {old_status} → {new_status}")
                break
                
    except Exception as e:
        logger.debug(f"Failed to sync single task status: {e}")
        # Don't raise the exception to avoid breaking the main workflow


# =============================================================================
# LOGGING AND REPORTING FUNCTIONS
# =============================================================================

def log_status_transition(logger, task_name: str, from_status: str, to_status: str, 
                         execution_time: float = None, additional_info: str = None) -> None:
    """
    Log task status transitions with consistent formatting.
    
    Args:
        logger: Logger instance
        task_name: Name of the task
        from_status: Previous status
        to_status: New status
        execution_time: Optional execution time for completion logs
        additional_info: Optional additional information to include
    """
    # Determine log level based on status
    if to_status == 'work-in-progress':
        log_level = 'info'
        icon = '🔄'
    elif to_status == 'done':
        log_level = 'info'
        icon = '✅'
    elif to_status == 'failed':
        log_level = 'error'
        icon = '❌'
    else:
        log_level = 'info'
        icon = '📝'
    
    # Build the log message
    if execution_time is not None:
        message = f"{icon} Task {task_name} → {to_status} ({execution_time:.2f}s)"
    else:
        message = f"{icon} Task {task_name} → {to_status}"
    
    if additional_info:
        message += f" - {additional_info}"
    
    # Log the message
    if log_level == 'error':
        logger.error(message)
    else:
        logger.info(message)

def log_task_failure(logger, task_name: str, error_type: str, error_details: str, 
                    execution_time: float = None) -> None:
    """
    Log detailed failure information for tasks.
    
    Args:
        logger: Logger instance
        task_name: Name of the failed task
        error_type: Type of error (timeout, command_not_found, etc.)
        error_details: Detailed error information
        execution_time: Optional execution time
    """
    time_info = f" ({execution_time:.2f}s)" if execution_time is not None else ""
    
    logger.error(f"💥 Task {task_name} failed{time_info}")
    logger.error(f"   Error Type: {error_type}")
    logger.error(f"   Details: {error_details}")
    logger.error(f"   Status: work-in-progress → failed")


# =============================================================================
# CORE TASK EXECUTION FUNCTIONS
# =============================================================================

def run_task(task: Dict[str, Any], yaml_file_path: str = None, all_tasks: List[Dict[str, Any]] = None) -> TaskResult:
    """
    Run a single task using cursor-agent command.
    
    Args:
        task: Task dictionary containing task information with 'name' and 'status' keys
        yaml_file_path: Optional path to YAML file for status synchronization
        all_tasks: Optional list of all tasks for context
        
    Returns:
        TaskResult: Structured result of the task execution
    """
    import time
    
    logger = logging.getLogger(__name__)
    
    # Extract task information from new structured format
    task_name = task.get('name', 'Unknown Task')
    task_status = task.get('status', 'pending')
    task_uuid = f"task-{hash(task_name)}"  # Generate a simple UUID based on task name
    task_prompt = task.get('prompt', '')
    
    logger.info(f"Starting task: {task_name} (status: {task_status})")
    
    # Check if task is already completed
    if task_status == 'done':
        logger.info(f"⏭️  Skipping task '{task_name}' - already completed")
        return TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=True,
            return_code=0,
            stdout="Task already completed",
            stderr="",
            execution_time=0.0,
            error_message=""
        )
    
    # Check if task previously failed (optional: you can choose to retry or skip)
    if task_status == 'failed':
        # logger.warning(f"⚠️  Task '{task_name}' previously failed - retrying...")
        # Uncomment the following lines if you want to skip failed tasks instead of retrying
        logger.info(f"⏭️  Skipping task '{task_name}' - previously failed")
        return TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=False,
            return_code=1,
            stdout="",
            stderr="Task previously failed",
            execution_time=0.0,
            error_message="Task previously failed"
        )
    
    # Update task status to work-in-progress before execution
    old_status = task.get('status', 'pending')
    task['status'] = 'work-in-progress'
    log_status_transition(logger, task_name, old_status, 'work-in-progress')
    
    # Sync status to YAML file if path is provided
    if yaml_file_path:
        sync_task_status_on_update(yaml_file_path, task_name, 'work-in-progress', all_tasks or [])
    
    start_time = time.time()
    
    try:
        # Build the cursor command using the task name as the prompt
        cmd = ['cursor', 'agent', task_prompt, '-p', '--force', '--output-format', 'text']
        
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.getcwd()
        )
        
        execution_time = time.time() - start_time
        
        # Update task status based on execution result
        if result.returncode == 0:
            task['status'] = 'done'
            log_status_transition(logger, task_name, 'work-in-progress', 'done', execution_time)
            # Sync status to YAML file if path is provided
            if yaml_file_path:
                sync_task_status_on_update(yaml_file_path, task_name, 'done', all_tasks or [])
        else:
            task['status'] = 'failed'
            log_status_transition(logger, task_name, 'work-in-progress', 'failed', execution_time, 
                                f"exit code: {result.returncode}")
            log_task_failure(logger, task_name, "command_failed", 
                           f"Command failed with exit code {result.returncode}", execution_time)
            # Sync status to YAML file if path is provided
            if yaml_file_path:
                sync_task_status_on_update(yaml_file_path, task_name, 'failed', all_tasks or [])
        
        # Create result object
        task_result = TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=result.returncode == 0,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time=execution_time
        )
        
        if result.returncode != 0:
            task_result.error_message = f"Command failed with exit code {result.returncode}"
        
        return task_result
        
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        task['status'] = 'failed'
        log_status_transition(logger, task_name, 'work-in-progress', 'failed', execution_time, 
                            "timeout after 5 minutes")
        log_task_failure(logger, task_name, "timeout", 
                        "Task execution timed out after 5 minutes", execution_time)
        # Sync status to YAML file if path is provided
        if yaml_file_path:
            sync_task_status_on_update(yaml_file_path, task_name, 'failed', all_tasks or [])
        return TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=False,
            return_code=-1,
            stdout="",
            stderr="",
            execution_time=execution_time,
            error_message="Task execution timed out after 5 minutes"
        )
        
    except FileNotFoundError:
        execution_time = time.time() - start_time
        task['status'] = 'failed'
        log_status_transition(logger, task_name, 'work-in-progress', 'failed', execution_time, 
                            "command not found")
        log_task_failure(logger, task_name, "command_not_found", 
                        "'cursor' command not found. Please ensure cursor CLI is installed.", execution_time)
        # Sync status to YAML file if path is provided
        if yaml_file_path:
            sync_task_status_on_update(yaml_file_path, task_name, 'failed', all_tasks or [])
        return TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=False,
            return_code=-1,
            stdout="",
            stderr="",
            execution_time=execution_time,
            error_message="'cursor' command not found. Please ensure cursor CLI is installed."
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        task['status'] = 'failed'
        log_status_transition(logger, task_name, 'work-in-progress', 'failed', execution_time, 
                            f"unexpected error: {str(e)}")
        log_task_failure(logger, task_name, "unexpected_error", 
                        f"Unexpected error: {str(e)}", execution_time)
        # Sync status to YAML file if path is provided
        if yaml_file_path:
            sync_task_status_on_update(yaml_file_path, task_name, 'failed', all_tasks or [])
        return TaskResult(
            task_uuid=task_uuid,
            task_name=task_name,
            success=False,
            return_code=-1,
            stdout="",
            stderr="",
            execution_time=execution_time,
            error_message=f"Unexpected error: {str(e)}"
        )


def run_tasks_concurrently(tasks: List[Dict[str, Any]], max_workers: int = 4, yaml_file_path: str = None) -> List[TaskResult]:
    """
    Run multiple tasks concurrently using ThreadPoolExecutor.
    
    Args:
        tasks: List of task dictionaries
        max_workers: Maximum number of concurrent workers
        yaml_file_path: Optional path to YAML file for status synchronization
        
    Returns:
        List[TaskResult]: List of task execution results
    """
    logger = logging.getLogger(__name__)
    
    if not tasks:
        logger.info("No tasks to execute.")
        return []
    
    logger.info(f"Starting execution of {len(tasks)} task(s) with {max_workers} worker(s)...")
    
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(run_task, task, yaml_file_path, tasks): task 
            for task in tasks
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Handle exceptions that occur during task execution
                task_name = task.get('name', 'Unknown Task')
                task_uuid = f"task-{hash(task_name)}"
                logger.error(f"💥 Exception in task {task_name}: {str(e)}")
                
                error_result = TaskResult(
                    task_uuid=task_uuid,
                    task_name=task_name,
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=0.0,
                    error_message=f"Exception during execution: {str(e)}"
                )
                results.append(error_result)
    
    return results


# =============================================================================
# REPORTING AND SUMMARY FUNCTIONS
# =============================================================================

def print_execution_summary(results: List[TaskResult], tasks: List[Dict[str, Any]] = None) -> None:
    """
    Print a comprehensive summary of task execution results.
    
    Args:
        results: List of task execution results
        tasks: Optional list of original tasks to show final status summary
    """
    logger = logging.getLogger(__name__)
    
    if not results:
        logger.info("No tasks were executed.")
        return
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_time = sum(r.execution_time for r in results)
    
    # Print final status summary table if tasks are provided
    if tasks:
        logger.info(f"\n{'='*60}")
        logger.info(f"FINAL STATUS SUMMARY")
        logger.info(f"{'='*60}")
        for task in tasks:
            task_name = task.get('name', 'Unknown Task')
            final_status = task.get('status', 'unknown')
            status_icon = "✅" if final_status == "done" else "❌" if final_status == "failed" else "⏳"
            logger.info(f"{status_icon} {task_name:<30} → {final_status}")
        logger.info(f"{'='*60}")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"EXECUTION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total tasks: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Total execution time: {total_time:.2f}s")
    logger.info(f"{'='*80}")
    
    # Show successful tasks
    if successful:
        logger.info(f"\n✅ SUCCESSFUL TASKS ({len(successful)}):")
        for result in successful:
            logger.info(f"  ✓ {result.task_name} ({result.task_uuid}) - {result.execution_time:.2f}s")
    
    # Show failed tasks with details
    if failed:
        logger.error(f"\n❌ FAILED TASKS ({len(failed)}):")
        for result in failed:
            logger.error(f"  ✗ {result.task_name} ({result.task_uuid}) - {result.execution_time:.2f}s")
            if result.error_message:
                logger.error(f"    Error: {result.error_message}")
            if result.stderr:
                # Truncate stderr to avoid overwhelming output
                stderr_preview = result.stderr[:200] + "..." if len(result.stderr) > 200 else result.stderr
                logger.error(f"    Stderr: {stderr_preview}")
            if result.stdout:
                # Show stdout for failed tasks (might contain useful info)
                stdout_preview = result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
                logger.error(f"    Stdout: {stdout_preview}")
    
    # Overall status
    if len(failed) == 0:
        logger.info(f"\n🎉 All tasks completed successfully!")
    else:
        logger.error(f"\n⚠️  {len(failed)} task(s) failed out of {len(results)} total.")


# =============================================================================
# FILE AND YAML PROCESSING FUNCTIONS
# =============================================================================

def validate_file_path(file_path: str) -> Path:
    """
    Validate that the provided file path exists and is accessible.
    
    Args:
        file_path: The file path to validate
        
    Returns:
        Path: A Path object representing the validated file
        
    Raises:
        SystemExit: If the file doesn't exist or is not accessible
    """
    logger = logging.getLogger(__name__)
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"File '{file_path}' does not exist.")
        logger.error("Please check the path and try again.")
        sys.exit(1)
    
    if not path.is_file():
        logger.error(f"'{file_path}' is not a file.")
        logger.error("Please provide a valid file path.")
        sys.exit(1)
    
    if not os.access(path, os.R_OK):
        logger.error(f"Cannot read file '{file_path}'.")
        logger.error("Please check file permissions.")
        sys.exit(1)
    
    return path


def load_yaml_file(file_path: Path) -> dict:
    """
    Load and parse a YAML file safely.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        dict: Parsed YAML content
        
    Raises:
        SystemExit: If YAML parsing fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = yaml.safe_load(file)
            return content
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML syntax in '{file_path}'.")
        logger.error(f"YAML Error: {e}")
        logger.error("Please check the YAML syntax and try again.")
        sys.exit(1)
    except UnicodeDecodeError as e:
        logger.error(f"Cannot decode file '{file_path}' as UTF-8.")
        logger.error(f"Encoding Error: {e}")
        logger.error("Please ensure the file is encoded in UTF-8.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to read file '{file_path}'.")
        logger.error(f"Error: {e}")
        sys.exit(1)


def validate_yaml_content(content: dict) -> list:
    """
    Validate that the YAML content has the expected structure.
    
    Args:
        content: Parsed YAML content
        
    Returns:
        list: List of structured task dictionaries with name and status
        
    Raises:
        SystemExit: If content structure is invalid
    """
    logger = logging.getLogger(__name__)
    
    if content is None:
        logger.error("YAML file is empty or contains no data.")
        logger.error("Please ensure the file contains valid YAML content.")
        sys.exit(1)
    
    if not isinstance(content, dict):
        logger.error("YAML content must be a dictionary/object.")
        logger.error(f"Found: {type(content).__name__}")
        logger.error("Please ensure the YAML file has a proper structure.")
        sys.exit(1)
    
    # Check for tasks key
    if 'tasks' not in content:
        logger.error("YAML file must contain a 'tasks' key.")
        logger.error(f"Available keys: {list(content.keys())}")
        logger.error("Please ensure the YAML file has a 'tasks' section.")
        sys.exit(1)
    
    tasks = content['tasks']
    
    if not isinstance(tasks, list):
        logger.error("'tasks' must be a list.")
        logger.error(f"Found: {type(tasks).__name__}")
        logger.error("Please ensure 'tasks' is formatted as a list.")
        sys.exit(1)
    
    if len(tasks) == 0:
        logger.warning("No tasks found in the YAML file.")
        logger.warning("The tasks list is empty.")
        return []
    
    # Convert raw YAML tasks to structured format with name and status
    structured_tasks = []
    for task in tasks:
        if isinstance(task, dict):
            # Extract task name from various possible keys
            task_name = task.get('Name') or task.get('name') or str(task)
            # Extract status, defaulting to 'pending' if not specified
            task_status = task.get('Status') or task.get('status') or 'pending'
            task_prompt = task.get('Prompt') or task.get('Prompt') or None
            
            structured_task = {
                "name": task_name,
                "status": task_status,
                "prompt": task_prompt
            }
            structured_tasks.append(structured_task)
        elif isinstance(task, str):
            task_prompt = task.get('Prompt') or task.get('Prompt') or None
            # Handle case where task is just a string
            structured_task = {
                "name": task_name,
                "status": "pending",
                "prompt": task_prompt
            }
            structured_tasks.append(structured_task)
        else:
            logger.warning(f"Skipping invalid task format: {task}")
    
    logger.info(f"Successfully loaded {len(structured_tasks)} task(s) from YAML file.")
    return structured_tasks


def load_yaml(path: str) -> List[Dict[str, Any]]:
    """
    Load and validate a YAML configuration file containing tasks.
    
    This function combines file validation, YAML parsing, and content validation
    into a single, clean interface.
    
    Args:
        path: Path to the YAML configuration file
        
    Returns:
        List[Dict[str, Any]]: List of validated task dictionaries
        
    Raises:
        SystemExit: If file validation, YAML parsing, or content validation fails
    """
    logger = logging.getLogger(__name__)
    
    # Step 1: Validate file path
    config_file = validate_file_path(path)
    logger.info(f"Configuration file validated: {config_file}")
    
    # Step 2: Load and parse YAML content
    yaml_content = load_yaml_file(config_file)
    logger.info("YAML file loaded successfully.")
    
    # Step 3: Validate YAML content structure
    tasks = validate_yaml_content(yaml_content)
    
    logger.info("YAML processing complete!")
    return tasks


# =============================================================================
# CLI ARGUMENT PARSING
# =============================================================================

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Cursor CLI tool for AI workflow management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path /path/to/config.yaml
  %(prog)s --path ./features/demo.yaml
  %(prog)s --path ./features/demo.yaml --verbose
  %(prog)s --work-dir ./target --path ./features/demo-1.yaml
        """
    )
    
    parser.add_argument(
        "--path",
        required=True,
        type=str,
        help="Path to the configuration file (required)"
    )
    
    parser.add_argument(
        "--work-dir",
        required=True,
        type=str,
        default=os.getcwd(),
        help="Working directory to execute in (defaults to current directory)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    args = parser.parse_args()
    
    # Validate --work-dir exists and is a directory
    work_dir = Path(args.work_dir).expanduser().resolve()
    if not work_dir.exists() or not work_dir.is_dir():
        parser.error(f"--work-dir 路径不存在或不是目录: {work_dir}")
    
    # Normalize back to string for downstream usage
    args.work_dir = str(work_dir)
    
    return args


# =============================================================================
# MAIN APPLICATION ENTRY POINT
# =============================================================================

def main():
    """
    Main entry point for the cursor CLI tool.
    
    Orchestrates the complete workflow:
    1. Parse command line arguments
    2. Set up logging
    3. Load and validate YAML configuration
    4. Execute tasks concurrently
    5. Report results and exit with appropriate code
    """
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Set up logging system
        setup_logging(verbose=args.verbose)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Cursor CLI tool...")
        
        # Apply working directory
        if args.work_dir:
            os.chdir(args.work_dir)
            logger.info(f"Working directory set to: {os.getcwd()}")
        
        # Load and validate YAML configuration
        tasks = load_yaml(args.path)
        logger.info(f"Ready to process {len(tasks)} task(s).")
        
        # Execute tasks if any are available
        if tasks:
            logger.info("Starting task execution...")
            
            # Execute tasks concurrently with 4 workers
            results = run_tasks_concurrently(tasks, max_workers=4, yaml_file_path=args.path)
            
            # Print comprehensive execution summary
            print_execution_summary(results, tasks)
            
            logger.info("Task execution complete!")
            
            # Exit with error code if any tasks failed
            failed_tasks = [r for r in results if not r.success]
            if failed_tasks:
                logger.error(f"Exiting with error code due to {len(failed_tasks)} failed task(s).")
                sys.exit(1)
        else:
            logger.info("No tasks to execute.")
        
        logger.info("Cursor CLI tool completed successfully!")
        
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.warning("Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()