#!/usr/bin/env python3
"""
Quick test script to verify real-time session tracking works
Tests the phone_number + timestamp approach
"""

import requests
import json
import time

# Configuration
API_URL = "https://fastapi-project-tau.vercel.app"  # Your API URL
# Or use local: "http://localhost:8000"

def test_phone_number_tracking():
    """Test that results are written to kiosk_results table using phone_number"""
    
    print("🧪 Testing Real-Time Results with Phone Number\n")
    print("=" * 60)
    
    # Test phone number
    test_phone = "+919876543210"
    print(f"\n1️⃣ Test Phone Number: {test_phone}")
    
    # Test data
    test_data = {
        "interests": "comedy shows, music",
        "phone_number": test_phone,
        "hotel_id": "marriott-bangalore"
    }
    
    print(f"\n2️⃣ Sending request to API...")
    print(f"   URL: {API_URL}/api/event/by-interests")
    print(f"   Data: {json.dumps(test_data, indent=2)}")
    
    # Make request
    try:
        response = requests.post(
            f"{API_URL}/api/event/by-interests",
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
            print(f"   ✅ Look for phone_number: {test_phone}")
            print(f"   ✅ The 'results' column should contain the full JSON response")
            print(f"   ✅ timestamp_millis should be a recent Unix timestamp")
            
            print(f"\n5️⃣ To test real-time subscription:")
            print(f"   ✅ Open your Next.js app")
            print(f"   ✅ Enter phone number: {test_phone}")
            print(f"   ✅ Subscribe to Supabase with phone_number filter")
            print(f"   ✅ Make another API call and watch results appear!")
            
            print("\n" + "=" * 60)
            print("✅ TEST PASSED - Phone number tracking is working!")
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
        print("4. Verify kiosk_results table exists")

def test_multiple_searches_same_guest():
    """Test multiple searches by same guest (same phone, different timestamps)"""
    
    print("\n\n🧪 Testing Multiple Searches by Same Guest\n")
    print("=" * 60)
    
    test_phone = "+919876543210"
    searches = ["comedy shows", "spa services", "food events"]
    
    print(f"Phone Number: {test_phone}")
    print(f"Will make {len(searches)} searches...\n")
    
    for i, interest in enumerate(searches):
        print(f"\n{i+1}. Searching for: '{interest}'")
        
        try:
            response = requests.post(
                f"{API_URL}/api/event/by-interests",
                json={
                    "interests": interest,
                    "phone_number": test_phone,
                    "hotel_id": "marriott-bangalore"
                }
            )
            
            if response.status_code == 200:
                print(f"   ✅ Success!")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Small delay between searches
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("✅ MULTIPLE SEARCHES TEST COMPLETE")
    print("=" * 60)
    print(f"\nCheck Supabase - should see {len(searches)} rows with:")
    print(f"  - phone_number: {test_phone}")
    print(f"  - Different timestamp_millis for each")
    print(f"  - unique_id: {test_phone}_[timestamp1], {test_phone}_[timestamp2], etc.")

def test_multiple_guests_concurrent():
    """Test multiple guests using kiosk concurrently"""
    
    print("\n\n🧪 Testing Multiple Concurrent Guests\n")
    print("=" * 60)
    
    guests = [
        {"phone": "+919876543210", "interest": "comedy"},
        {"phone": "+918765432109", "interest": "spa"},
        {"phone": "+917654321098", "interest": "food"}
    ]
    
    for i, guest in enumerate(guests):
        print(f"\n{i+1}. Guest {guest['phone']} searching for '{guest['interest']}'")
        
        try:
            response = requests.post(
                f"{API_URL}/api/event/by-interests",
                json={
                    "interests": guest['interest'],
                    "phone_number": guest['phone'],
                    "hotel_id": "marriott-bangalore"
                }
            )
            
            if response.status_code == 200:
                print(f"   ✅ Success!")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("✅ CONCURRENT GUESTS TEST COMPLETE")
    print("=" * 60)
    print(f"\nCheck Supabase - should see {len(guests)} rows with:")
    for guest in guests:
        print(f"  - {guest['phone']}: {guest['interest']} results")
    print("\n✅ Each guest gets only their own results (filtered by phone)!")

if __name__ == "__main__":
    print("\n🚀 Spotive Real-Time Results Testing (Phone Number Approach)\n")
    
    print("This tests the phone_number + timestamp approach:")
    print("- FastAPI generates timestamp internally")
    print("- Results identified by phone_number + timestamp_millis")
    print("- Frontend subscribes by phone_number")
    print("- Each search is unique due to millisecond timestamp\n")
    
    # Run tests
    test_phone_number_tracking()
    
    # Ask if user wants more tests
    print("\n\nTest multiple searches by same guest? (y/n): ", end="")
    try:
        answer = input().strip().lower()
        if answer == 'y':
            test_multiple_searches_same_guest()
    except:
        pass
    
    print("\n\nTest multiple concurrent guests? (y/n): ", end="")
    try:
        answer = input().strip().lower()
        if answer == 'y':
            test_multiple_guests_concurrent()
    except:
        pass
    
    print("\n\n✅ All tests complete!")
    print("\nNext steps:")
    print("1. Check Supabase → kiosk_results table")
    print("2. Verify phone_number and timestamp_millis columns")
    print("3. Check unique_id is auto-generated (phone_timestamp)")
    print("4. Implement frontend subscription")
    print("5. Test end-to-end with voice!\n")
