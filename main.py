"""
main.py

The front door. Run this to start PYROS:  python main.py

Its only job is to start everything else IN THE RIGHT ORDER:
1. Load and verify settings/API keys
2. Initialize the memory database
3. Confirm the model router can actually reach at least one provider
4. Launch the desktop window (once ui/window.py exists)

Nothing "smart" happens in this file — no chat logic, no tool logic.
That separation is intentional: if PYROS crashes on startup, you know
immediately it's one of these 3 steps, not buried somewhere in the brain.
"""
import sys
import core.settings as settings
import memory.history_store as history
import memory.vector_store as vectors  # noqa: F401 (imported to confirm it loads cleanly)
from core.model_router import LLMRouter


def startup_checks() -> bool:
    """Runs before anything else opens. Returns True if safe to continue."""
    print(f"Starting {settings.APP_NAME}...")

    print("[1/3] Checking API keys...")
    keys_ok = settings.check_keys_loaded()
    if not keys_ok:
        print("Cannot continue — fix your .env file and try again.")
        return False

    print("[2/3] Initializing memory database...")
    try:
        history.init_db()
        print("      Memory database ready.")
    except Exception as e:
        print(f"      Memory database failed to initialize: {e}")
        return False

    print("[3/3] Checking model router connectivity...")
    try:
        router = LLMRouter()
        status = router.status()
        available = [name for name, info in status.items() if info["available"]]
        if not available:
            print("      No providers currently available (all rate-limited or misconfigured).")
        else:
            print(f"      Ready — {len(available)} provider/key(s) available: {', '.join(available)}")
    except Exception as e:
        print(f"      Router check failed: {e}")
        return False

    print(f"{settings.APP_NAME} startup checks complete.\n")
    return True


def main():
    if not startup_checks():
        sys.exit(1)

    # Once ui/window.py is built and wired up, this replaces the block below:
    #
    #     from ui.window import launch_ui
    #     launch_ui()
    #
    # For now, a simple text-based loop so you can test PYROS end-to-end
    # from the terminal before the graphical window exists.
    from core.orchestrator import run as run_agent

    print("PYROS is ready. Type your message, or 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Shutting down PYROS.")
            break
        if not user_input:
            continue

        try:
            result = run_agent(user_input)
            print(f"PYROS: {result['reply']}\n")
        except RuntimeError as e:
            print(f"[Rate limit] {e}\n")
        except Exception as e:
            print(f"[Error] {e}\n")


if __name__ == "__main__":
    main()