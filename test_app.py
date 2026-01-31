from fastapi.testclient import TestClient
from main import app
import logic

client = TestClient(app)

API_KEY = "honeypot-secret-key-123"

def test_auth():
    # No Key
    response = client.post("/api/honeypot", json={"conversation_id": "1", "message": "hi"})
    assert response.status_code == 401
    
    # Wrong Key
    response = client.post("/api/honeypot", json={"conversation_id": "1", "message": "hi"}, headers={"x-api-key": "wrong"})
    assert response.status_code == 403
    
    # Correct Key
    response = client.post("/api/honeypot", json={"conversation_id": "1", "message": "hi"}, headers={"x-api-key": API_KEY})
    assert response.status_code == 200

def test_scam_detection():
    # Innocent message
    response = client.post("/api/honeypot", json={"conversation_id": "2", "message": "Hello friend"}, headers={"x-api-key": API_KEY})
    data = response.json()
    assert data["is_scam"] is False
    assert data["persona_state"] == "idle"

    # Scam message
    scam_msg = "You have won a lottery! Urgent! Send money to bank account 123456789."
    response = client.post("/api/honeypot", json={"conversation_id": "3", "message": scam_msg}, headers={"x-api-key": API_KEY})
    data = response.json()
    assert data["is_scam"] is True
    assert data["confidence"] > 0.0
    # First state transition should be IDLE -> CONFUSED
    assert data["persona_state"] == "confused"

def test_state_machine():
    cid = "state_test"
    headers = {"x-api-key": API_KEY}
    
    # Reset state
    logic._conversation_states[cid] = "idle"
    
    # 1. Scam message -> Confused
    msg1 = "Urgent lottery winner! Click link."
    res1 = client.post("/api/honeypot", json={"conversation_id": cid, "message": msg1}, headers=headers)
    assert res1.json()["persona_state"] == "confused", f"Expected confused, got {res1.json()['persona_state']}"
    
    # 2. More pressure -> Trusting
    msg2 = "You must pay tax now."
    res2 = client.post("/api/honeypot", json={"conversation_id": cid, "message": msg2}, headers=headers)
    assert res2.json()["persona_state"] == "trusting", f"Expected trusting, got {res2.json()['persona_state']}"
    
    # 3. Payment details -> Extracting
    msg3 = "Send to UPI abc@upi"
    res3 = client.post("/api/honeypot", json={"conversation_id": cid, "message": msg3}, headers=headers)
    assert res3.json()["persona_state"] == "extracting", f"Expected extracting, got {res3.json()['persona_state']}"
    assert "abc@upi" in res3.json()["extracted_entities"]["upi_ids"]

def test_extraction():
    msg = "Pay to 1234567890 and IFSC ABCD0123456 and upi test@okicici"
    response = client.post("/api/honeypot", json={"conversation_id": "ext", "message": msg}, headers={"x-api-key": API_KEY})
    data = response.json()
    assert "1234567890" in data["extracted_entities"]["bank_accounts"]
    assert "ABCD0123456" in data["extracted_entities"]["ifsc_codes"]
    assert "test@okicici" in data["extracted_entities"]["upi_ids"]

def test_robustness():
    # Mock an error in logic
    original_detect = logic.detect_scam
    def mock_error(msg):
        raise ValueError("Simulated crash")
    
    logic.detect_scam = mock_error
    
    try:
        response = client.post("/api/honeypot", json={"conversation_id": "crash", "message": "hi"}, headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert data["is_scam"] is False
        assert data["agent_reply"] == "I am sorry, I did not catch that."
        print("Robustness test passed.")
    finally:
        logic.detect_scam = original_detect

def run_tests():
    print("Running tests...")
    try:
        test_auth()
        print("Auth tests passed.")
        test_scam_detection()
        print("Scam detection tests passed.")
        test_state_machine()
        print("State machine tests passed.")
        test_extraction()
        print("Extraction tests passed.")
        test_robustness()
        print("ALL TESTS PASSED.")
    except AssertionError as e:
        print(f"Test Failed: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
