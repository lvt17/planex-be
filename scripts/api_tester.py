import requests
import json
import uuid
import sys

BASE_URL = "http://localhost:5000/api"

def run_tests():
    print("🚀 Starting API Integration Tests...")
    
    # 1. Register/Login
    unique_user = f"user_{uuid.uuid4().hex[:6]}"
    email = f"{unique_user}@example.com"
    password = "password123"
    
    print(f"Checking Auth with {email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "username": unique_user,
        "email": email,
        "password": password
    })
    
    if reg_res.status_code not in [201, 409]:
        print(f"❌ Registration failed: {reg_res.text}")
        sys.exit(1)
        
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    
    if login_res.status_code != 200:
        print(f"❌ Login failed: {login_res.text}")
        sys.exit(1)
        
    token = login_res.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Auth successful.")

    # 2. Create Task
    print("Creating a task...")
    task_res = requests.post(f"{BASE_URL}/tasks", headers=headers, json={
        "name": "Live Test Task",
        "content": "Testing from script",
        "price": 250.0
    })
    
    if task_res.status_code != 201:
        print(f"❌ Task creation failed: {task_res.text}")
        sys.exit(1)
    
    task_id = task_res.json()['id']
    print(f"✅ Task created (ID: {task_id}).")

    # 3. Check MCP Integration
    print("Checking AI/MCP context...")
    mcp_res = requests.get(f"{BASE_URL}/mcp/context", headers=headers)
    if mcp_res.status_code == 200:
        print("✅ MCP Context endpoint working.")
    else:
        print(f"❌ MCP Context failed: {mcp_res.text}")

    # 4. Update Progress via AI endpoint
    print("Updating progress via AI API...")
    update_res = requests.put(f"{BASE_URL}/mcp/tasks/{task_id}/progress", headers=headers, json={
        "progress": 90,
        "notes": "Testing AI progress update"
    })
    
    if update_res.status_code == 200:
        print("✅ AI Progress update successful.")
    else:
        print(f"❌ AI Update failed: {update_res.text}")

    print("\n🎉 All API checks passed!")

if __name__ == "__main__":
    try:
        run_tests()
    except requests.exceptions.ConnectionError:
        print("❌ Error: API server not running. Please run 'python run.py' first.")
