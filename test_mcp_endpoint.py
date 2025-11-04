"""
Test script for the MCP-based event filtering endpoint
Run this after starting the API with: uvicorn app.main:app --reload
"""

import requests
import json

# API base URL
BASE_URL = "http://127.0.0.1:8000"

def test_mcp_endpoint():
    """Test the /api/events/by-preferences endpoint"""
    
    print("=" * 60)
    print("Testing MCP-Based Event Filtering Endpoint")
    print("=" * 60)
    
    # Test cases with different preferences
    test_cases = [
        {
            "date": "2025-11-15",
            "preferences": "music, entertainment, outdoor",
            "description": "Music lover looking for outdoor entertainment"
        },
        {
            "date": "2025-11-09",
            "preferences": "kids, family-friendly, fun",
            "description": "Family with kids looking for fun activities"
        },
        {
            "date": "2025-11-12",
            "preferences": "spiritual, cultural, free",
            "description": "Budget-conscious spiritual seeker"
        },
        {
            "date": "2025-11-11",
            "preferences": "adventure, outdoor, active, morning",
            "description": "Adventure seeker wanting morning activities"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test Case {i}: {test_case['description']}")
        print(f"{'=' * 60}")
        print(f"Date: {test_case['date']}")
        print(f"Preferences: {test_case['preferences']}")
        print()
        
        try:
            # Make POST request
            response = requests.post(
                f"{BASE_URL}/api/events/by-preferences",
                json={
                    "date": test_case["date"],
                    "preferences": test_case["preferences"]
                },
                timeout=30
            )
            
            # Check response
            if response.status_code == 200:
                data = response.json()
                
                if data["success"]:
                    print(f"✅ SUCCESS!")
                    print(f"   Total events on date: {data['total_events_on_date']}")
                    print(f"   Matched events: {data['matched_events']}")
                    print(f"   Source: {data['source']}")
                    print()
                    
                    # Display top results
                    print("Top Results:")
                    for result in data["top_results"]:
                        print(f"\n   Rank #{result['rank']}: {result['event_details']['name']}")
                        print(f"   Category: {result['event_details']['category']}")
                        print(f"   Location: {result['event_details']['location']}")
                        print(f"   Price: {result['event_details']['price']}")
                        print(f"   AI Suggestion: {result['suggestion']}")
                else:
                    print(f"❌ FAILED: {data.get('message', 'Unknown error')}")
                    
            elif response.status_code == 404:
                data = response.json()
                print(f"⚠️  NO EVENTS FOUND: {data.get('message')}")
                
            else:
                print(f"❌ ERROR: Status code {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ CONNECTION ERROR: Is the API running?")
            print("   Start it with: uvicorn app.main:app --reload")
            break
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    print(f"\n{'=' * 60}")
    print("Testing Complete!")
    print("=" * 60)

def test_random_event():
    """Quick test of the random event endpoint"""
    print("\n" + "=" * 60)
    print("Bonus Test: Random Event Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/random-event", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                print("✅ Random event endpoint working!")
                print(f"   Event: {data['event_details']['name']}")
                print(f"   Suggestion: {data['suggestion']}")
            else:
                print(f"❌ FAILED: {data.get('message')}")
        else:
            print(f"❌ ERROR: Status code {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    # Check if API is running
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            print("\n✅ API is running!")
        else:
            print("\n⚠️  API responded but might not be ready")
    except:
        print("\n❌ API is not running!")
        print("Start it with: uvicorn app.main:app --reload")
        exit(1)
    
    # Run tests
    test_mcp_endpoint()
    test_random_event()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("=" * 60)

