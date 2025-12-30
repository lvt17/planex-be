import json

def test_mcp_query_tasks(client, auth_header):
    # Create some tasks first
    client.post('/api/tasks', headers=auth_header, json={'name': 'Task 1'})
    client.post('/api/tasks', headers=auth_header, json={'name': 'Task 2'})
    
    response = client.get('/api/mcp/tasks', headers=auth_header)
    if response.status_code != 200:
        print(f"DEBUG MCP: {response.get_json()}")
    assert response.status_code == 200
    data = response.get_json()
    assert 'tasks' in data
    assert len(data['tasks']) >= 2
    # Check MCP format (description instead of content, etc.)
    assert 'description' in data['tasks'][0]

def test_mcp_update_progress(client, auth_header):
    task_res = client.post('/api/tasks', headers=auth_header, json={'name': 'MCP Task'})
    task_id = task_res.get_json()['id']
    
    response = client.put(f'/api/mcp/tasks/{task_id}/progress', headers=auth_header, json={
        'progress': 75,
        'notes': 'AI completed part of the work'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['task']['progress'] == 75.0
    assert 'AI Update' in data['task']['notes']
