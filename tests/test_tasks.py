import json
from datetime import datetime, timedelta

def test_create_task(client, auth_header):
    response = client.post('/api/tasks', headers=auth_header, json={
        'name': 'Test Task',
        'content': 'This is a test task',
        'price': 100.0,
        'deadline': (datetime.utcnow() + timedelta(days=1)).isoformat()
    })
    if response.status_code != 201:
        print(f"DEBUG: {response.get_json()}")
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Test Task'
    assert data['price'] == 100.0

def test_task_progress_automation(client, auth_header):
    # 1. Create a task
    task_res = client.post('/api/tasks', headers=auth_header, json={
        'name': 'Parent Task'
    })
    if task_res.status_code != 201:
        print(f"DEBUG Parent: {task_res.get_json()}")
    task_id = task_res.get_json()['id']
    
    # 2. Add subtasks (workspaces)
    client.post(f'/api/workspaces/tasks/{task_id}/workspaces', headers=auth_header, json={
        'mini_task': 'Subtask 1',
        'loading': 0,
        'is_done': False
    })
    ws2_res = client.post(f'/api/workspaces/tasks/{task_id}/workspaces', headers=auth_header, json={
        'mini_task': 'Subtask 2',
        'loading': 0,
        'is_done': False
    })
    ws2_id = ws2_res.get_json()['id']
    
    # 3. Update a subtask and check parent progress
    client.put(f'/api/workspaces/{ws2_id}', headers=auth_header, json={
        'loading': 50,
        'is_done': False
    })
    
    # Parent progress should be (0 + 50) / 2 = 25
    parent_res = client.get(f'/api/tasks/{task_id}', headers=auth_header)
    assert parent_res.get_json()['state'] == 25.0

def test_income_trigger_on_completion(client, auth_header):
    # 1. Create a task with price
    task_res = client.post('/api/tasks', headers=auth_header, json={
        'name': 'Paid Task',
        'price': 500.0
    })
    task_id = task_res.get_json()['id']
    
    # 2. Mark as done
    client.put(f'/api/tasks/{task_id}', headers=auth_header, json={
        'is_done': True
    })
    
    # 3. Check income stats
    income_res = client.get('/api/income', headers=auth_header)
    assert income_res.get_json()['total_income'] == 500.0
