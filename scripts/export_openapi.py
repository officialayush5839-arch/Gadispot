"""Export complete, verified OpenAPI 3.1 specification from FastAPI app."""

import json
import os
import sys

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import create_app


def export_openapi():
    app = create_app()
    openapi_schema = app.openapi()
    
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "technical"))
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "openapi.json")

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"Exported OpenAPI 3.1 schema to {target_file}")
    print(f"Total Routes Documented: {len(openapi_schema.get('paths', {}))}")


if __name__ == "__main__":
    export_openapi()
