"""
test_setup.py

Run this from your PYROS root folder:  python test_setup.py
"""
import sys

def check(label, fn):
    try:
        fn()
        print(f"[PASS] {label}")
        return True
    except Exception as e:
        print(f"[FAIL] {label} -> {e}")
        return False


results = []

def test_settings():
    import core.settings as settings
    ok = settings.check_keys_loaded()
    if not ok:
        raise Exception("one or more keys missing from .env")

results.append(check("Settings load API keys", test_settings))

def test_history():
    import memory.history_store as history
    history.init_db()
    history.add_message("user", "test message from test_setup.py")
    recent = history.get_recent_messages(limit=5)
    assert any(m["content"] == "test message from test_setup.py" for m in recent)

results.append(check("History store (SQLite) read/write", test_history))

def test_vectors():
    import memory.vector_store as vectors
    vectors.add_conversation_memory("The sky is blue and the grass is green.", tag="test")
    hits = vectors.search_conversation_memory("what color is the sky", top_k=1)
    assert len(hits) > 0

results.append(check("Vector store (ChromaDB) embed/search", test_vectors))

def test_router():
    from core.model_router import LLMRouter
    router = LLMRouter()
    response = router.chat([{"role": "user", "content": "Reply with exactly: PYROS ONLINE"}])
    reply = response.choices[0].message.content
    print(f"        model replied: {reply.strip()}")

results.append(check("Model router (live API call)", test_router))

def test_orchestrator():
    import core.orchestrator as orchestrator
    result = orchestrator.run("Say hello in exactly three words.")
    print(f"        orchestrator replied: {result['reply'].strip()}")
    assert result["message_id"]

results.append(check("Orchestrator full pipeline", test_orchestrator))

print("\n" + "=" * 40)
passed = sum(results)
print(f"{passed}/{len(results)} checks passed")
if passed == len(results):
    print("Everything is working. Safe to move on to the next step.")
else:
    print("Fix the FAILed steps above before continuing.")
    sys.exit(1)