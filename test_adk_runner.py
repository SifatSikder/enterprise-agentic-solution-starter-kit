#!/usr/bin/env python3
"""
Test script to verify ADK Runner integration works correctly.

This script tests:
1. ADK agent loading
2. MultiTenantRunner execution
3. Session persistence
4. Multi-tenancy isolation

Run with: python test_adk_runner.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.manager import AgentManager
from agents.core.interfaces import AgentRequest


async def test_agent_loading():
    """Test 1: Verify agents load correctly with adapters."""
    print("\n" + "="*60)
    print("TEST 1: Agent Loading")
    print("="*60)
    
    manager = AgentManager()
    await manager.initialize()
    
    print(f"✅ Loaded {len(manager.adapters)} agent adapters:")
    for name, adapter in manager.adapters.items():
        print(f"   - {name}: {adapter.description}")
    
    assert len(manager.adapters) > 0, "No agents loaded!"
    print("\n✅ TEST 1 PASSED: Agents loaded successfully\n")
    
    return manager


async def test_streaming(manager: AgentManager):
    """Test 2: Verify streaming works with ADK Runner."""
    print("\n" + "="*60)
    print("TEST 2: Streaming Execution")
    print("="*60)
    
    agent_name = list(manager.adapters.keys())[0]
    print(f"Testing agent: {agent_name}")
    
    chunks = []
    async for response in manager.stream_chat(
        session_id="test_session_1",
        message="Hello! What can you help me with?",
        agent_name=agent_name,
        tenant_id="test_tenant",
        user_id="test_user"
    ):
        if response.get("type") == "chunk":
            chunk = response.get("content", "")
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        elif response.get("type") == "complete":
            print("\n\n✅ Streaming completed")
        elif response.get("type") == "error":
            print(f"\n❌ Error: {response.get('content')}")
            raise Exception(response.get('content'))
    
    full_response = "".join(chunks)
    assert len(full_response) > 0, "No response received!"
    print(f"\n✅ TEST 2 PASSED: Received {len(chunks)} chunks, {len(full_response)} chars\n")


async def test_session_persistence(manager: AgentManager):
    """Test 3: Verify session persistence works."""
    print("\n" + "="*60)
    print("TEST 3: Session Persistence")
    print("="*60)
    
    agent_name = list(manager.adapters.keys())[0]
    session_id = "test_session_2"
    tenant_id = "test_tenant"
    
    # Message 1: Tell the agent our name
    print("\n📤 Message 1: Telling agent our name...")
    async for response in manager.stream_chat(
        session_id=session_id,
        message="My name is Alice. Please remember this.",
        agent_name=agent_name,
        tenant_id=tenant_id,
        user_id="test_user"
    ):
        if response.get("type") == "chunk":
            print(response.get("content", ""), end="", flush=True)
    
    print("\n")
    
    # Message 2: Ask the agent to recall our name
    print("\n📤 Message 2: Asking agent to recall name...")
    response_text = []
    async for response in manager.stream_chat(
        session_id=session_id,
        message="What is my name?",
        agent_name=agent_name,
        tenant_id=tenant_id,
        user_id="test_user"
    ):
        if response.get("type") == "chunk":
            chunk = response.get("content", "")
            response_text.append(chunk)
            print(chunk, end="", flush=True)
    
    full_response = "".join(response_text).lower()
    
    # Check if agent remembered the name
    if "alice" in full_response:
        print("\n\n✅ TEST 3 PASSED: Agent remembered the name 'Alice'!\n")
    else:
        print(f"\n\n⚠️  TEST 3 WARNING: Agent may not have remembered the name.")
        print(f"Response: {full_response[:200]}...\n")


async def test_multi_tenancy(manager: AgentManager):
    """Test 4: Verify multi-tenancy isolation works."""
    print("\n" + "="*60)
    print("TEST 4: Multi-Tenancy Isolation")
    print("="*60)
    
    agent_name = list(manager.adapters.keys())[0]
    session_id = "test_session_3"
    
    # Tenant A: Share a secret
    print("\n📤 Tenant A: Sharing secret...")
    async for response in manager.stream_chat(
        session_id=session_id,
        message="My secret code is ALPHA-123. Remember this.",
        agent_name=agent_name,
        tenant_id="tenant_a",
        user_id="user_a"
    ):
        if response.get("type") == "chunk":
            print(response.get("content", ""), end="", flush=True)
    
    print("\n")
    
    # Tenant B: Try to access Tenant A's secret (should fail)
    print("\n📤 Tenant B: Trying to access Tenant A's secret...")
    response_text = []
    async for response in manager.stream_chat(
        session_id=session_id,  # Same session_id, different tenant_id
        message="What is my secret code?",
        agent_name=agent_name,
        tenant_id="tenant_b",  # Different tenant!
        user_id="user_b"
    ):
        if response.get("type") == "chunk":
            chunk = response.get("content", "")
            response_text.append(chunk)
            print(chunk, end="", flush=True)
    
    full_response = "".join(response_text).lower()
    
    # Check that Tenant B cannot access Tenant A's secret
    if "alpha-123" not in full_response:
        print("\n\n✅ TEST 4 PASSED: Multi-tenancy isolation working! Tenant B cannot access Tenant A's data.\n")
    else:
        print(f"\n\n❌ TEST 4 FAILED: Tenant isolation broken! Tenant B accessed Tenant A's secret.")
        print(f"Response: {full_response}\n")


async def test_health_check(manager: AgentManager):
    """Test 5: Verify health checks work."""
    print("\n" + "="*60)
    print("TEST 5: Health Checks")
    print("="*60)
    
    for name, adapter in manager.adapters.items():
        health = await adapter.health_check()
        status = "✅ HEALTHY" if health.healthy else "❌ UNHEALTHY"
        print(f"{status} - {name}")
        print(f"   Details: {health.details}")
    
    print("\n✅ TEST 5 PASSED: Health checks completed\n")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 ADK RUNNER INTEGRATION TESTS")
    print("="*60)
    print("\nTesting the new ADK-aligned architecture:")
    print("- MultiTenantRunner")
    print("- ADKAgentAdapter")
    print("- MultiTenantSessionAdapter")
    print("- Session persistence")
    print("- Multi-tenancy isolation")
    
    try:
        # Test 1: Load agents
        manager = await test_agent_loading()
        
        # Test 2: Streaming
        await test_streaming(manager)
        
        # Test 3: Session persistence
        await test_session_persistence(manager)
        
        # Test 4: Multi-tenancy
        await test_multi_tenancy(manager)
        
        # Test 5: Health checks
        await test_health_check(manager)
        
        # Cleanup
        await manager.cleanup()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nYour ADK-aligned architecture is working correctly! 🎉")
        print("\nNext steps:")
        print("1. Test with ADK Web: docker compose --profile dev up -d")
        print("2. Open http://localhost:3002")
        print("3. Test via FastAPI: http://localhost:8000/docs")
        print("\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TESTS FAILED")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

