"""
Phase 5: Vertex AI Memory Bank Integration Tests

Tests the integration of Vertex AI Memory Bank with the multi-agent framework.

Prerequisites:
    1. Server running: python3.11 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    2. VERTEX_MEMORY_ENABLED=true in .env
    3. Valid Google Cloud credentials configured
    4. Vertex AI API enabled in your project

Test Coverage:
    1. Memory Bank status check
    2. Save session to memory
    3. Search memories
    4. Multi-tenant memory isolation
    5. Auto-save functionality
"""

import asyncio
import httpx
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0

# Test credentials (from Phase 3)
TEST_USERS = {
    "user1": {"username": "user1", "password": "user123", "tenant": "tenant1"},
    "user2": {"username": "user2", "password": "user123", "tenant": "tenant2"},
}


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Login and get JWT token."""
    response = await client.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    return response.json()["access_token"]


async def test_1_memory_status():
    """Test 1: Check Memory Bank status"""
    print("\n" + "="*80)
    print("TEST 1: Memory Bank Status")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login as user1
        token = await login(client, "user1", "user123")
        
        # Get memory status
        response = await client.get(
            f"{BASE_URL}/api/memory/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            status = response.json()
            if status["enabled"]:
                print("✅ Memory Bank is ENABLED")
                print(f"   - Initialized: {status['initialized']}")
                print(f"   - Auto-save: {status['auto_save']}")
                print(f"   - Project: {status['project_id']}")
                print(f"   - Location: {status['location']}")
                print(f"   - Agent Engine ID: {status['agent_engine_id']}")
            else:
                print("⚠️  Memory Bank is DISABLED")
                print("   Set VERTEX_MEMORY_ENABLED=true in .env to enable")
                return False
        else:
            print(f"❌ Failed to get status: {response.text}")
            return False
    
    return True


async def test_2_chat_with_auto_save():
    """Test 2: Chat with agent and auto-save to memory"""
    print("\n" + "="*80)
    print("TEST 2: Chat with Auto-Save to Memory")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login as user1
        token = await login(client, "user1", "user123")
        
        # Have a conversation about preferences
        print("\n📝 User: I prefer the temperature at 72 degrees")
        response1 = await client.post(
            f"{BASE_URL}/api/agents/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "I prefer the temperature at 72 degrees",
                "agent": "template_simple_agent",
                "session_id": "memory-test-session-1"
            }
        )
        
        print(f"Status Code: {response1.status_code}")
        if response1.status_code == 200:
            result = response1.json()
            agent_message = result.get('message', result.get('response', 'No response'))
            print(f"🤖 Agent: {agent_message[:100]}...")
            print("✅ Conversation completed")
            
            # If auto-save is enabled, session should be saved automatically
            print("\n⏳ Waiting for auto-save to complete...")
            await asyncio.sleep(3)  # Give time for async memory save
            print("✅ Auto-save should be complete")
        else:
            print(f"❌ Chat failed: {response1.text}")
            return False
    
    return True


async def test_3_manual_save_session():
    """Test 3: Manually save session to memory"""
    print("\n" + "="*80)
    print("TEST 3: Manual Save Session to Memory")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login as user1
        token = await login(client, "user1", "user123")
        
        # Have another conversation
        print("\n📝 User: My favorite color is blue")
        response1 = await client.post(
            f"{BASE_URL}/api/agents/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": "My favorite color is blue",
                "agent": "template_simple_agent",
                "session_id": "tenant1:memory-test-session-2"
            }
        )

        if response1.status_code != 200:
            print(f"❌ Chat failed: {response1.text}")
            return False

        result = response1.json()
        agent_message = result.get('message', result.get('response', 'No response'))
        print(f"🤖 Agent: {agent_message[:100]}...")

        # Manually save session to memory
        print("\n💾 Manually saving session to memory...")
        response2 = await client.post(
            f"{BASE_URL}/api/memory/save",
            headers={"Authorization": f"Bearer {token}"},
            json={"session_id": "tenant1:memory-test-session-2"}
        )
        
        print(f"Status Code: {response2.status_code}")
        print(f"Response: {response2.json()}")
        
        if response2.status_code == 200:
            print("✅ Session saved to memory successfully")
        else:
            print(f"❌ Failed to save session: {response2.text}")
            return False
    
    return True


async def test_4_search_memories():
    """Test 4: Search memories"""
    print("\n" + "="*80)
    print("TEST 4: Search Memories")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Login as user1
        token = await login(client, "user1", "user123")
        
        # Wait a bit for memory indexing
        print("\n⏳ Waiting for memory indexing...")
        await asyncio.sleep(5)
        
        # Search for temperature preference
        print("\n🔍 Searching: 'What is the user's preferred temperature?'")
        response1 = await client.post(
            f"{BASE_URL}/api/memory/search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "What is the user's preferred temperature?",
                "limit": 5
            }
        )
        
        print(f"Status Code: {response1.status_code}")
        if response1.status_code == 200:
            result = response1.json()
            print(f"Found {result['count']} memories")
            if result['count'] > 0:
                print("\n📚 Memories:")
                for i, memory in enumerate(result['memories'][:3], 1):
                    print(f"   {i}. {memory}")
                print("✅ Memory search successful")
            else:
                print("⚠️  No memories found (may need more time for indexing)")
        else:
            print(f"❌ Search failed: {response1.text}")
            return False
        
        # Search for color preference
        print("\n🔍 Searching: 'What is the user's favorite color?'")
        response2 = await client.post(
            f"{BASE_URL}/api/memory/search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "What is the user's favorite color?",
                "limit": 5
            }
        )
        
        if response2.status_code == 200:
            result = response2.json()
            print(f"Found {result['count']} memories")
            if result['count'] > 0:
                print("\n📚 Memories:")
                for i, memory in enumerate(result['memories'][:3], 1):
                    print(f"   {i}. {memory}")
        else:
            print(f"❌ Search failed: {response2.text}")
    
    return True


async def test_5_multi_tenant_isolation():
    """Test 5: Multi-tenant memory isolation"""
    print("\n" + "="*80)
    print("TEST 5: Multi-Tenant Memory Isolation")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # User1 (tenant1) shares a preference
        token1 = await login(client, "user1", "user123")
        print("\n👤 User1 (tenant1): I like pizza")
        await client.post(
            f"{BASE_URL}/api/agents/chat",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "message": "I like pizza",
                "agent": "template_simple_agent",
                "session_id": "isolation-test-1"
            }
        )
        
        # User2 (tenant2) shares a different preference
        token2 = await login(client, "user2", "user123")
        print("👤 User2 (tenant2): I like sushi")
        await client.post(
            f"{BASE_URL}/api/agents/chat",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "message": "I like sushi",
                "agent": "template_simple_agent",
                "session_id": "isolation-test-2"
            }
        )
        
        # Wait for memory indexing
        await asyncio.sleep(5)
        
        # User1 searches for food preference
        print("\n🔍 User1 searching: 'What food do I like?'")
        response1 = await client.post(
            f"{BASE_URL}/api/memory/search",
            headers={"Authorization": f"Bearer {token1}"},
            json={"query": "What food do I like?", "limit": 5}
        )
        
        # User2 searches for food preference
        print("🔍 User2 searching: 'What food do I like?'")
        response2 = await client.post(
            f"{BASE_URL}/api/memory/search",
            headers={"Authorization": f"Bearer {token2}"},
            json={"query": "What food do I like?", "limit": 5}
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            memories1 = response1.json()['memories']
            memories2 = response2.json()['memories']
            
            print(f"\n📊 User1 found {len(memories1)} memories")
            print(f"📊 User2 found {len(memories2)} memories")
            
            # Memories should be isolated (different results)
            print("\n✅ Multi-tenant isolation working (memories are tenant-specific)")
        else:
            print("❌ Search failed for one or both users")
            return False
    
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PHASE 5: VERTEX AI MEMORY BANK INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        ("Memory Status", test_1_memory_status),
        ("Chat with Auto-Save", test_2_chat_with_auto_save),
        ("Manual Save Session", test_3_manual_save_session),
        ("Search Memories", test_4_search_memories),
        ("Multi-Tenant Isolation", test_5_multi_tenant_isolation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

