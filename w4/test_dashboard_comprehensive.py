#!/usr/bin/env python3
"""
Comprehensive automated test suite for Chat & Observability Dashboard.

Tests all levels (L1-L4) with various query types and verifies observability events.
"""

import requests
import time
import json
from typing import Dict, List, Any
from dataclasses import dataclass

MAIN_API = "http://localhost:8001"
DASHBOARD_API = "http://localhost:8002"

@dataclass
class TestCase:
    """Represents a single test case."""
    name: str
    level: str
    query: str
    session_id: str = None
    expected_tools: List[str] = None
    expected_chunks: bool = True
    min_chunks: int = 1
    max_processing_time: float = 15.0
    
class DashboardTester:
    """Automated tester for dashboard functionality."""
    
    def __init__(self):
        self.results = []
        self.session_counter = 0
        
    def new_session_id(self) -> str:
        """Generate a unique session ID for testing."""
        self.session_counter += 1
        return f"test-session-{self.session_counter:03d}"
    
    def run_test(self, test: TestCase) -> Dict[str, Any]:
        """Run a single test case."""
        print(f"\n{'='*60}")
        print(f"Test: {test.name}")
        print(f"Level: {test.level} | Query: {test.query[:50]}...")
        print('='*60)
        
        result = {
            "name": test.name,
            "level": test.level,
            "query": test.query,
            "passed": False,
            "errors": [],
            "warnings": [],
            "metrics": {}
        }
        
        try:
            # Step 1: Send query to API
            payload = {
                "query": test.query,
                "level": test.level
            }
            if test.session_id:
                payload["session_id"] = test.session_id
            
            start_time = time.time()
            response = requests.post(
                f"{MAIN_API}/query",
                json=payload,
                timeout=30
            )
            api_time = time.time() - start_time
            
            if response.status_code != 200:
                result["errors"].append(f"API returned status {response.status_code}")
                return result
            
            data = response.json()
            result["metrics"]["api_response_time"] = round(api_time, 3)
            result["metrics"]["processing_time"] = data.get("processing_time", 0)
            
            print(f"✅ API Response: {data['processing_time']}s")
            
            # Step 2: Wait for events to be logged
            time.sleep(1)
            
            # Step 3: Get latest query from dashboard
            queries_response = requests.get(f"{DASHBOARD_API}/api/queries", timeout=5)
            if queries_response.status_code != 200:
                result["errors"].append("Failed to fetch queries from dashboard")
                return result
            
            queries_data = queries_response.json()
            if not queries_data.get("queries"):
                result["errors"].append("No queries found in dashboard")
                return result
            
            latest_query = queries_data["queries"][0]
            query_id = latest_query["query_id"]
            
            # Step 4: Get events for this query
            events_response = requests.get(f"{DASHBOARD_API}/api/query/{query_id}", timeout=5)
            if events_response.status_code != 200:
                result["errors"].append("Failed to fetch events from dashboard")
                return result
            
            events_data = events_response.json()
            events = events_data.get("events", [])
            
            result["metrics"]["num_events"] = len(events)
            print(f"📊 Events logged: {len(events)}")
            
            # Step 5: Verify events
            self._verify_events(test, events, result)
            
            # Step 6: Check processing time
            if data["processing_time"] > test.max_processing_time:
                result["warnings"].append(
                    f"Processing time {data['processing_time']}s exceeds target {test.max_processing_time}s"
                )
            
            # Step 7: Verify answer quality
            if not data.get("answer"):
                result["errors"].append("Empty answer received")
            elif len(data["answer"]) < 10:
                result["warnings"].append("Answer seems too short")
            
            # Mark as passed if no errors
            result["passed"] = len(result["errors"]) == 0
            
            if result["passed"]:
                print(f"✅ Test PASSED")
            else:
                print(f"❌ Test FAILED: {', '.join(result['errors'])}")
            
            if result["warnings"]:
                print(f"⚠️  Warnings: {', '.join(result['warnings'])}")
            
        except Exception as e:
            result["errors"].append(f"Exception: {str(e)}")
            print(f"❌ Test FAILED with exception: {e}")
        
        return result
    
    def _verify_events(self, test: TestCase, events: List[Dict], result: Dict):
        """Verify that expected events are present."""
        event_types = [e["event_type"] for e in events]
        
        # Check for query_received
        if "query_received" not in event_types:
            result["errors"].append("Missing 'query_received' event")
        
        # Check for response_generated
        if "response_generated" not in event_types:
            result["errors"].append("Missing 'response_generated' event")
        
        # Check for retrieval (if expected)
        if test.expected_chunks:
            if "retrieval_completed" not in event_types:
                result["errors"].append("Missing 'retrieval_completed' event")
            else:
                # Verify chunk count
                retrieval_event = next(e for e in events if e["event_type"] == "retrieval_completed")
                num_chunks = retrieval_event["data"].get("num_chunks", 0)
                result["metrics"]["num_chunks"] = num_chunks
                
                if num_chunks < test.min_chunks:
                    result["errors"].append(
                        f"Expected at least {test.min_chunks} chunks, got {num_chunks}"
                    )
                else:
                    print(f"📚 Retrieved {num_chunks} chunks")
        
        # Check for tool execution (if expected)
        if test.expected_tools:
            tool_events = [e for e in events if e["event_type"] == "tool_executed"]
            tools_used = [e["data"].get("tool_name") for e in tool_events]
            result["metrics"]["tools_used"] = tools_used
            
            for expected_tool in test.expected_tools:
                if expected_tool not in tools_used:
                    result["errors"].append(f"Expected tool '{expected_tool}' not executed")
                else:
                    print(f"🔧 Tool executed: {expected_tool}")
        
        # Check for memory loading (L4)
        if test.level == "L4":
            if "memory_loaded" not in event_types:
                result["warnings"].append("Missing 'memory_loaded' event for L4 query")
            else:
                memory_event = next(e for e in events if e["event_type"] == "memory_loaded")
                num_turns = memory_event["data"].get("num_turns", 0)
                result["metrics"]["memory_turns"] = num_turns
                print(f"💾 Memory loaded: {num_turns} turns")
    
    def run_test_suite(self):
        """Run the complete test suite."""
        print("\n" + "="*60)
        print("GeekBrain AI — Dashboard Comprehensive Test Suite")
        print("="*60)
        
        # Check services
        if not self._check_services():
            print("\n❌ Services not ready. Exiting.")
            return
        
        # Define test cases
        test_cases = self._define_test_cases()
        
        # Run tests
        for test in test_cases:
            result = self.run_test(test)
            self.results.append(result)
            time.sleep(2)  # Pause between tests
        
        # Print summary
        self._print_summary()
    
    def _check_services(self) -> bool:
        """Check if all required services are running."""
        print("\n🔍 Checking services...")
        
        services = [
            ("Main API", f"{MAIN_API}/health"),
            ("Dashboard", DASHBOARD_API),
            ("Monitoring API", "http://localhost:8000/")  # Root endpoint, not /health
        ]
        
        all_ok = True
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name} is running")
                else:
                    print(f"❌ {name} returned status {response.status_code}")
                    all_ok = False
            except Exception as e:
                print(f"❌ {name} is not accessible: {e}")
                all_ok = False
        
        return all_ok
    
    def _define_test_cases(self) -> List[TestCase]:
        """Define all test cases."""
        tests = []
        
        # ── L1 Tests ──────────────────────────────────────
        tests.append(TestCase(
            name="L1.1: Basic Team Information",
            level="L1",
            query="Who is the Team Platform lead?",
            expected_chunks=True,
            min_chunks=3,
            max_processing_time=5.0
        ))
        
        tests.append(TestCase(
            name="L1.2: Policy Information",
            level="L1",
            query="What is the deployment freeze window?",
            expected_chunks=True,
            min_chunks=3,
            max_processing_time=5.0
        ))
        
        tests.append(TestCase(
            name="L1.3: Technical Documentation",
            level="L1",
            query="How do I configure the monitoring agent?",
            expected_chunks=True,
            min_chunks=3,
            max_processing_time=5.0
        ))
        
        # ── L2 Tests ──────────────────────────────────────
        tests.append(TestCase(
            name="L2.1: Version Conflict Resolution",
            level="L2",
            query="What is PaymentGW's API rate limit?",
            expected_chunks=True,
            min_chunks=5,
            max_processing_time=8.0
        ))
        
        tests.append(TestCase(
            name="L2.2: Multi-Document Query",
            level="L2",
            query="What are the SLA requirements for all services?",
            expected_chunks=True,
            min_chunks=5,
            max_processing_time=8.0
        ))
        
        # ── L3 Tests ──────────────────────────────────────
        tests.append(TestCase(
            name="L3.1: Historical Cost Query",
            level="L3",
            query="What was PaymentGW's total infrastructure cost in Q1 2026?",
            expected_tools=["query_database"],
            expected_chunks=False,
            max_processing_time=10.0
        ))
        
        tests.append(TestCase(
            name="L3.2: Live Metrics Query",
            level="L3",
            query="What is PaymentGW's current p99 latency?",
            expected_tools=["get_service_metrics"],
            expected_chunks=False,
            max_processing_time=10.0
        ))
        
        tests.append(TestCase(
            name="L3.3: Multi-Tool Query",
            level="L3",
            query="Is NotificationSvc meeting its SLA targets?",
            expected_tools=["query_database", "get_service_metrics"],
            expected_chunks=False,
            max_processing_time=10.0
        ))
        
        tests.append(TestCase(
            name="L3.4: List Services",
            level="L3",
            query="What services are being monitored?",
            expected_tools=["list_services"],
            expected_chunks=False,
            max_processing_time=10.0
        ))
        
        tests.append(TestCase(
            name="L3.5: Incident History",
            level="L3",
            query="Show me recent incidents for PaymentGW",
            expected_tools=["get_incident_history"],
            expected_chunks=False,
            max_processing_time=10.0
        ))
        
        # ── L4 Tests ──────────────────────────────────────
        session_id = self.new_session_id()
        
        tests.append(TestCase(
            name="L4.1: Multi-Turn Turn 1",
            level="L4",
            query="Service nào có chi phí cao nhất tháng 3/2026?",
            session_id=session_id,
            expected_tools=["query_database"],
            expected_chunks=False,
            max_processing_time=12.0
        ))
        
        tests.append(TestCase(
            name="L4.2: Multi-Turn Turn 2 (Pronoun)",
            level="L4",
            query="Tại sao chi phí của nó tăng đột biến?",
            session_id=session_id,
            expected_chunks=True,
            min_chunks=3,
            max_processing_time=12.0
        ))
        
        tests.append(TestCase(
            name="L4.3: Multi-Turn Turn 3 (Context)",
            level="L4",
            query="Team nào chịu trách nhiệm?",
            session_id=session_id,
            expected_chunks=True,
            min_chunks=2,
            max_processing_time=12.0
        ))
        
        return tests
    
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Group by level
        levels = {}
        for r in self.results:
            level = r["level"]
            if level not in levels:
                levels[level] = {"passed": 0, "failed": 0}
            if r["passed"]:
                levels[level]["passed"] += 1
            else:
                levels[level]["failed"] += 1
        
        print("\nResults by Level:")
        for level in sorted(levels.keys()):
            stats = levels[level]
            total_level = stats["passed"] + stats["failed"]
            print(f"  {level}: {stats['passed']}/{total_level} passed")
        
        # Failed tests
        if failed > 0:
            print("\n❌ Failed Tests:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  - {r['name']}")
                    for error in r["errors"]:
                        print(f"    • {error}")
        
        # Performance summary
        print("\n⏱ Performance Summary:")
        for r in self.results:
            if "processing_time" in r["metrics"]:
                status = "✅" if r["passed"] else "❌"
                print(f"  {status} {r['name']}: {r['metrics']['processing_time']}s")
        
        print("\n" + "="*60)
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("\n📝 Detailed results saved to: test_results.json")

def main():
    """Main entry point."""
    tester = DashboardTester()
    tester.run_test_suite()

if __name__ == "__main__":
    main()
