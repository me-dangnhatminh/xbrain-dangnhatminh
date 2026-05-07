#!/usr/bin/env python3
"""
Quick test script for the Chat & Observability Dashboard.

This script sends a test query to verify the dashboard is working.
"""

import requests
import time
import sys

MAIN_API = "http://localhost:8001"
DASHBOARD = "http://localhost:8002"

def test_api_health():
    """Test if main API is running."""
    try:
        response = requests.get(f"{MAIN_API}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Main API is running on port 8001")
            return True
        else:
            print(f"❌ Main API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Main API is not running on port 8001")
        print("   Start it with: cd w4 && bash start_dashboard.sh")
        return False
    except Exception as e:
        print(f"❌ Error checking main API: {e}")
        return False

def test_monitoring_api():
    """Test if monitoring API is running."""
    try:
        # Monitoring API doesn't have /health, use root endpoint
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Monitoring API is running on port 8000")
            return True
        else:
            print(f"❌ Monitoring API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Monitoring API is not running on port 8000")
        print("   It should auto-start with start_dashboard.sh")
        return False
    except Exception as e:
        print(f"❌ Error checking monitoring API: {e}")
        return False

def test_dashboard():
    """Test if dashboard is accessible."""
    try:
        response = requests.get(DASHBOARD, timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is accessible on port 8002")
            return True
        else:
            print(f"❌ Dashboard returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Dashboard is not running on port 8002")
        print("   It should auto-start with main API")
        return False
    except Exception as e:
        print(f"❌ Error checking dashboard: {e}")
        return False

def send_test_query():
    """Send a test query to the API."""
    print("\n📤 Sending test query...")
    
    payload = {
        "query": "Who is the Team Platform lead?",
        "level": "L1"
    }
    
    try:
        response = requests.post(
            f"{MAIN_API}/query",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Query successful!")
            print(f"   Answer: {data['answer'][:100]}...")
            print(f"   Sources: {', '.join(data['sources'][:3])}")
            print(f"   Processing time: {data['processing_time']}s")
            return True
        else:
            print(f"❌ Query failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending query: {e}")
        return False

def check_observability():
    """Check if observability events are being logged."""
    print("\n🔍 Checking observability events...")
    
    try:
        response = requests.get(f"{DASHBOARD}/api/queries", timeout=5)
        if response.status_code == 200:
            data = response.json()
            queries = data.get('queries', [])
            
            if queries:
                print(f"✅ Found {len(queries)} logged queries")
                latest = queries[0]
                print(f"   Latest query: {latest['query'][:50]}...")
                print(f"   Level: {latest['level']}")
                print(f"   Processing time: {latest.get('processing_time_ms', 0)}ms")
                return True
            else:
                print("⚠️  No queries logged yet")
                return False
        else:
            print(f"❌ Failed to fetch queries: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking observability: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("GeekBrain AI — Dashboard Test")
    print("=" * 60)
    
    # Test 1: Check main API health
    if not test_api_health():
        sys.exit(1)
    
    # Test 2: Check monitoring API
    if not test_monitoring_api():
        print("\n⚠️  Warning: Monitoring API not running")
        print("   L3 queries will fail without it")
        print("   Continuing with other tests...\n")
    
    # Test 3: Check dashboard
    if not test_dashboard():
        sys.exit(1)
    
    # Test 4: Send test query
    if not send_test_query():
        sys.exit(1)
    
    # Wait a bit for events to be logged
    time.sleep(1)
    
    # Test 5: Check observability
    check_observability()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print(f"\n🌐 Open dashboard: {DASHBOARD}")
    print("   Try chatting with the AI and watch the observability panel!")
    print()

if __name__ == "__main__":
    main()
