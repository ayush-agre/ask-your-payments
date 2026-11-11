import json
import os
import sys

def check_specs():
    fastapi_path = r"C:\Users\AYUSH\Downloads\src\spec\fastapi_openapi.json"
    erp_path = r"C:\Users\AYUSH\Downloads\src\spec\erp_mock_openapi.json"

    with open(fastapi_path, "r", encoding="utf-8") as f:
        fastapi = json.load(f)
    with open(erp_path, "r", encoding="utf-8") as f:
        erp = json.load(f)

    print("FastAPI version:", fastapi.get("openapi"))
    print("ERP version:", erp.get("openapi"))

    print("\nFastAPI tags:")
    tags_in_fastapi = set()
    for path, path_obj in fastapi.get("paths", {}).items():
        for method, op in path_obj.items():
            if isinstance(op, dict):
                tags_in_fastapi.update(op.get("tags", []))
    print(tags_in_fastapi)

    print("\nERP tags defined:")
    print(erp.get("tags", []))

    print("\nERP responses:")
    print(list(erp.get("components", {}).get("responses", {}).keys()))

    print("\nERP securitySchemes:")
    print(list(erp.get("components", {}).get("securitySchemes", {}).keys()))

if __name__ == "__main__":
    check_specs()
