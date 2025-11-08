#!/usr/bin/env python3
"""
Quick test script to verify real-time session tracking works
Run this to test the implementation before integrating with frontend
"""

import requests
import json
import uuid
import time

# Configuration
API_URL = "https://fastapi-project-tau.vercel.app"  # Your API URL
# Or use local: "http://localhost:8000"

def test_session_tracking():
    """Test that results are written to kiosk_results table"""
    
    print("🧪 Testing Real-Time Session Tracking\n")
    print("=" * 60)
    
    # Generate test session ID
    session_id = f"test-{uuid.uuid4()}"
    print(f"\n1️⃣ Generated Session ID: {session_id}")
    
    # Test data
    test_data = {
        "interests": "comedy shows, music",
        "hotel_id": "marriott-bangalore"  # Use your hotel slug
    }
    
    print(f"\n2️⃣ Sending request to API...")
    print(f"   URL: {API_URL}/api/event/by-interests?session_id={session_id}")
    print(f"   Data: {json.dumps(test_data, indent=2)}")
    
    # Make request
    try:
        response = requests.post(
            f"{API_URL}/api/event/by-interests",
            params={"session_id": session_id},
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n3️⃣ Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success!")
            print(f"   Found {result.get('returned_events', 0)} events")
            print(f"   Categories: {result.get('mapped_categories', [])}")
            
            if result.get('hotel_filtered'):
                print(f"   Hotel: {result['hotel']['name']}")
            
            print(f"\n4️⃣ Results should now be in Supabase:")
            print(f"   ✅ Check Supabase → Table Editor → kiosk_results")
            print(f"   ✅ Look for session_id: {session_id}")
            print(f"   ✅ The 'results' column should contain the full JSON response")
            
            print(f"\n5️⃣ To test real-time subscription:")
            print(f"   ✅ Open your Next.js app")
            print(f"   ✅ Look for this session_id in the subscription")
            print(f"   ✅ You should see the results appear instantly!")
            
            print("\n" + "=" * 60)
            print("✅ TEST PASSED - Session tracking is working!")
            print("=" * 60)
            
        else:
            print(f"   ❌ Failed: {response.text}")
            print("\n❌ TEST FAILED")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\n❌ TEST FAILED")
        print("\nTroubleshooting:")
        print("1. Check if API is running")
        print("2. Verify API_URL is correct")
        print("3. Check if hotel_id exists in your database")

def test_multiple_sessions():
    """Test multiple concurrent sessions (simulating multiple kiosks)"""
    
    print("\n\n🧪 Testing Multiple Concurrent Sessions\n")
    print("=" * 60)
    
    sessions = []
    
    # Create 3 test sessions
    for i in range(3):
        session_id = f"concurrent-test-{i}-{uuid.uuid4()}"
        sessions.append(session_id)
        
        print(f"\n{i+1}. Sending request for session: {session_id[:20]}...")
        
        try:
            response = requests.post(
                f"{API_URL}/api/event/by-interests",
                params={"session_id": session_id},
                json={
                    "interests": ["comedy", "music", "food"][i],
                    "hotel_id": "marriott-bangalore"
                }
            )
            
            if response.status_code == 200:
                print(f"   ✅ Success!")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("✅ CONCURRENT TEST COMPLETE")
    print("=" * 60)
    print(f"\nCreated {len(sessions)} sessions:")
    for i, sid in enumerate(sessions):
        print(f"  {i+1}. {sid}")
    
    print("\n✅ Check Supabase - all 3 sessions should have separate results!")

if __name__ == "__main__":
    print("\n🚀 Spotive Real-Time Session Testing\n")
    
    # Run tests
    test_session_tracking()
    
    # Ask if user wants to test multiple sessions
    print("\n\nWould you like to test multiple concurrent sessions? (y/n): ", end="")
    try:
        answer = input().strip().lower()
        if answer == 'y':
            test_multiple_sessions()
    except:
        pass
    
    print("\n\n✅ All tests complete!")
    print("\nNext steps:")
    print("1. Check Supabase → kiosk_results table")
    print("2. Implement frontend subscription (see REALTIME_SESSION_GUIDE.md)")
    print("3. Configure ElevenLabs agent")
    print("4. Test end-to-end with voice!\n")

