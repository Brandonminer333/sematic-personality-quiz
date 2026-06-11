"""CLI entrypoint for the quiz generation pipeline."""

from api.generation.orchestrator import main

if __name__ == "__main__":
    raise SystemExit(main())
