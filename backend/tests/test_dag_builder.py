import pytest
from core.dag_builder import DAGBuilder, SubTask

def test_dag_builder_single_task():
    builder = DAGBuilder()
    dag = builder.build_single_task("coding", "Write hello world")
    assert dag.is_valid
    assert len(dag.subtasks) == 1
    assert len(dag.execution_order) == 1
    assert dag.critical_path == ["task_0"]

def test_dag_builder_parallel_and_sequential():
    builder = DAGBuilder()
    tasks = [
        SubTask(id="t1", description="Fetch data A", task_type="research"),
        SubTask(id="t2", description="Fetch data B", task_type="research"),
        SubTask(id="t3", description="Merge data", task_type="analysis", dependencies=["t1", "t2"]),
        SubTask(id="t4", description="Generate report", task_type="writing", dependencies=["t3"]),
    ]
    dag = builder.build(tasks)
    assert dag.is_valid
    assert len(dag.validation_errors) == 0
    assert len(dag.execution_order) == 3
    
    # Level 0 should have t1 and t2 in parallel
    assert set(dag.execution_order[0].task_ids) == {"t1", "t2"}
    # Level 1 should have t3
    assert dag.execution_order[1].task_ids == ["t3"]
    # Level 2 should have t4
    assert dag.execution_order[2].task_ids == ["t4"]
    # Critical path should end with t4
    assert dag.critical_path[-1] == "t4"

def test_dag_builder_cycle_detection():
    builder = DAGBuilder()
    tasks = [
        SubTask(id="a", description="Task A", task_type="coding", dependencies=["b"]),
        SubTask(id="b", description="Task B", task_type="coding", dependencies=["a"]),
    ]
    dag = builder.build(tasks)
    assert not dag.is_valid
    assert any("Circular dependency" in err for err in dag.validation_errors)

def test_dag_builder_missing_dependency():
    builder = DAGBuilder()
    tasks = [
        SubTask(id="x", description="Task X", task_type="coding", dependencies=["non_existent"]),
    ]
    dag = builder.build(tasks)
    assert not dag.is_valid
    assert any("depends on non-existent task" in err for err in dag.validation_errors)
