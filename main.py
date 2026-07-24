"""
main.py

Starts PYROS end-to-end with all tools wired in.
"""
import sys
import core.settings as settings
import memory.history_store as history
import memory.vector_store as vectors  # noqa: F401
from core.model_router import LLMRouter


def load_tools():
    tools = []
    tool_functions = {}
    loaded_names = []
    failed = []

    try:
        from actions.launch import open_application, TOOL_SCHEMA as launch_schema
        tools.append(launch_schema)
        tool_functions["open_application"] = open_application
        loaded_names.append("open_application (launch.py)")
    except Exception as e:
        failed.append(f"launch.py -> {e}")

    try:
        from actions.browse import open_url, TOOL_SCHEMA as browse_schema
        tools.append(browse_schema)
        tool_functions["open_url"] = open_url
        loaded_names.append("open_url (browse.py)")
    except Exception as e:
        failed.append(f"browse.py -> {e}")

    try:
        from actions.mail import send_email, TOOL_SCHEMA as mail_schema
        tools.append(mail_schema)
        tool_functions["send_email"] = send_email
        loaded_names.append("send_email (mail.py)")
    except Exception as e:
        failed.append(f"mail.py -> {e}")

    print("Tools loaded:")
    for name in loaded_names:
        print(f"  [OK] {name}")
    for fail in failed:
        print(f"  [SKIPPED] {fail}")
    print()

    return tools, tool_functions


def startup_checks() -> bool:
    print(f"Starting {settings.APP_NAME}...")

    print("[1/3] Checking API keys...")
    if not settings.check_keys_loaded():
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
            print("      No providers currently available.")
        else:
            print(f"      Ready — {len(available)} provider/key(s) available.")
    except Exception as e:
        print(f"      Router check failed: {e}")
        return False

    print(f"{settings.APP_NAME} startup checks complete.\n")
    return True


def main():
    if not startup_checks():
        sys.exit(1)

    tools, tool_functions = load_tools()

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
            result = run_agent(user_input, tools=tools, tool_functions=tool_functions)
            print(f"PYROS: {result['reply']}\n")
            if result.get("tool_calls", 0) > 0:
                print(f"      (used {result['tool_calls']} tool round(s))\n")
        except RuntimeError as e:
            print(f"[Rate limit] {e}\n")
        except Exception as e:
            print(f"[Error] {e}\n")


if __name__ == "__main__":
    main()