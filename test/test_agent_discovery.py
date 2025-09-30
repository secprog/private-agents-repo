#!/usr/bin/env python3
"""
Test script to verify agent discovery is working
"""

import asyncio
import httpx

async def test_agent_endpoints():
    """Test if agent endpoints are accessible"""
    
    # Test endpoints
    endpoints = [
        "http://localhost:8000",  # Orchestrator
        "http://localhost:8001",  # Cybersecurity Agent
        "http://localhost:8002",  # DevOps Agent
    ]
    
    print("🔍 Testing agent endpoints...")
    
    for endpoint in endpoints:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Test health endpoint
                health_response = await client.get(f"{endpoint}/health")
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print(f"✅ {endpoint}/health - {health_data}")
                else:
                    print(f"❌ {endpoint}/health - Status: {health_response.status_code}")
                
                # Test agent card endpoint
                try:
                    card_response = await client.get(f"{endpoint}/.well-known/agent-card.json")
                    if card_response.status_code == 200:
                        card_data = card_response.json()
                        print(f"✅ {endpoint}/.well-known/agent-card.json - Agent ID: {card_data.get('agent_id', 'Unknown')}")
                    else:
                        print(f"⚠️  {endpoint}/.well-known/agent-card.json - Status: {card_response.status_code}")
                except Exception as e:
                    print(f"⚠️  {endpoint}/.well-known/agent-card.json - Error: {e}")
                
                # Test A2A endpoint (mounted by ADK)
                try:
                    a2a_response = await client.post(f"{endpoint}", json={"test": "message"})
                    print(f"✅ {endpoint} - Status: {a2a_response.status_code}")
                except Exception as e:
                    print(f"⚠️  {endpoint} - Error: {e}")
                    
        except Exception as e:
            print(f"❌ {endpoint} - Connection failed: {e}")
        
        print()

async def test_orchestrator_discovery():
    """Test orchestrator's agent discovery"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/agents")
            if response.status_code == 200:
                agents_data = response.json()
                print("🎯 Orchestrator discovered agents:")
                for agent in agents_data.get("agents", []):
                    print(f"  - {agent.get('agent_id', 'Unknown')} at {agent.get('endpoint', 'Unknown')}")
            else:
                print(f"❌ Orchestrator agents endpoint - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Orchestrator agents endpoint - Error: {e}")

if __name__ == "__main__":
    print("🚀 Agent Platform Discovery Test")
    print("=" * 50)
    
    asyncio.run(test_agent_endpoints())
    print("=" * 50)
    asyncio.run(test_orchestrator_discovery())
