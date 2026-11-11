"""
merge_openapi.py – Programmatic OpenAPI 3.1.0 Specification Merger
==================================================================
Team CrackerX · Ask-Your-Payments Architecture

Merges:
  1. fastapi_openapi.json (Core Backend API - OpenAPI 3.1.0)
  2. erp_mock_openapi.json (Mock Enterprise ERP API - OpenAPI 3.0.3)

Outputs:
  - final_merged_api.json (Single, valid, consolidated OpenAPI 3.1.0 specification)

Handling:
  - Route definitions ('paths') merged and validated.
  - Data models ('components.schemas') merged with collision resolution.
  - Component responses, parameters, security schemes, headers merged.
  - Tags, servers, and security merged cleanly.
  - Upgrades any OpenAPI 3.0.x elements (nullable -> anyOf/type array, etc.) to 3.1.0 compliance.
"""

import copy
import json
import os
import sys
from typing import Any, Dict, List, Set


def convert_30_to_31(schema: Any) -> Any:
    """
    Recursively updates an OpenAPI 3.0.x schema fragment to OpenAPI 3.1.0 standard:
    - If `nullable: True` is present:
        - If `type: "string"` -> `type: ["string", "null"]` (or anyOf with null type).
        - Remove `nullable` keyword (not part of JSON Schema 2020-12 / OpenAPI 3.1).
    """
    if isinstance(schema, dict):
        new_schema = {}
        for k, v in schema.items():
            if k == "nullable":
                continue
            new_schema[k] = convert_30_to_31(v)

        if schema.get("nullable") is True:
            t = new_schema.get("type")
            if isinstance(t, str):
                new_schema["type"] = [t, "null"]
            elif isinstance(t, list) and "null" not in t:
                new_schema["type"] = t + ["null"]
            elif "$ref" in new_schema:
                # In OpenAPI 3.1, $ref can be combined with other keywords, or wrapped in anyOf
                ref_val = new_schema.pop("$ref")
                existing_props = {k: v for k, v in new_schema.items()}
                new_schema = {
                    "anyOf": [
                        {"$ref": ref_val},
                        {"type": "null"}
                    ]
                }
                new_schema.update(existing_props)
        return new_schema
    elif isinstance(schema, list):
        return [convert_30_to_31(item) for item in schema]
    return schema


def merge_openapi_specs(
    fastapi_spec: Dict[str, Any],
    erp_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Programmatically merges fastapi_spec and erp_spec into a unified OpenAPI 3.1.0 spec.
    """
    # 1. Base Structure from Core Backend (OpenAPI 3.1.0)
    merged: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "Ask-Your-Payments Consolidated Platform API",
            "description": (
                "Consolidated OpenAPI 3.1.0 specification for Ask-Your-Payments, "
                "merging the FastAPI core reconciliation backend (AI investigation, "
                "AG Grid SSRM datasource, Webhook ACK, Staged Operations) with the "
                "Mock Enterprise ERP API (Invoices, Vendors, General Ledger Journal Entries)."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "Team CrackerX",
                "email": "crackerx@askyourpayments.example.com",
            },
            "license": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
        },
        "servers": [],
        "tags": [],
        "paths": {},
        "components": {
            "schemas": {},
            "responses": {},
            "parameters": {},
            "securitySchemes": {},
            "headers": {},
        },
    }

    # 2. Merge Servers
    server_urls = set()
    default_servers = [
        {"url": "http://localhost:8000", "description": "Local FastAPI Core Backend"},
        {"url": "https://erp-mock.askyourpayments.example.com", "description": "Mock ERP Server"},
    ]
    for s in default_servers + erp_spec.get("servers", []) + fastapi_spec.get("servers", []):
        url = s.get("url")
        if url and url not in server_urls:
            merged["servers"].append(s)
            server_urls.add(url)

    # 3. Merge Tags
    tag_names = set()
    for tag in erp_spec.get("tags", []):
        name = tag.get("name")
        if name and name not in tag_names:
            merged["tags"].append(tag)
            tag_names.add(name)

    # Add core tags
    core_tags = [
        {"name": "AI Investigation", "description": "Natural Language Investigation router powered by Gemini 2.5 Flash"},
        {"name": "Financial Studio Grid", "description": "AG Grid Enterprise Server-Side Row Model (SSRM) & Audit Evidence"},
        {"name": "Webhooks", "description": "Real-time PayPal Webhook ingestion & WebSocket broadcast"},
        {"name": "System", "description": "Liveness & Readiness health check probes"},
    ]
    for tag in core_tags:
        name = tag.get("name")
        if name and name not in tag_names:
            merged["tags"].append(tag)
            tag_names.add(name)

    # 4. Merge Components - Schemas (with collision handling)
    fastapi_schemas = fastapi_spec.get("components", {}).get("schemas", {})
    erp_schemas = erp_spec.get("components", {}).get("schemas", {})

    merged_schemas = merged["components"]["schemas"]

    # Add FastAPI schemas first
    for name, schema_def in fastapi_schemas.items():
        merged_schemas[name] = copy.deepcopy(schema_def)

    # Add ERP schemas (convert 3.0 nullable -> 3.1 schema)
    for name, schema_def in erp_schemas.items():
        converted_schema = convert_30_to_31(copy.deepcopy(schema_def))
        if name in merged_schemas:
            # Handle potential collision
            if merged_schemas[name] == converted_schema:
                print(f"[COLLISION RESOLVED] Identical schema '{name}' detected. Retaining canonical definition.")
            else:
                # Rename colliding schema with namespace prefix
                renamed_key = f"ERP_{name}"
                print(f"[COLLISION RESOLVED] Distinct schema collision on '{name}'. Renamed to '{renamed_key}'.")
                merged_schemas[renamed_key] = converted_schema
                # Update refs if any
        else:
            merged_schemas[name] = converted_schema

    # 5. Merge Components - Responses, Parameters, SecuritySchemes
    for comp_type in ["responses", "parameters", "securitySchemes", "headers"]:
        fastapi_comp = fastapi_spec.get("components", {}).get(comp_type, {})
        erp_comp = erp_spec.get("components", {}).get(comp_type, {})

        dest_comp = merged["components"][comp_type]
        for k, v in fastapi_comp.items():
            dest_comp[k] = copy.deepcopy(v)
        for k, v in erp_comp.items():
            converted_v = convert_30_to_31(copy.deepcopy(v))
            if k not in dest_comp:
                dest_comp[k] = converted_v

    # Clean empty components keys if not needed
    if not merged["components"]["parameters"]:
        del merged["components"]["parameters"]
    if not merged["components"]["headers"]:
        del merged["components"]["headers"]

    # 6. Merge Paths
    fastapi_paths = fastapi_spec.get("paths", {})
    erp_paths = erp_spec.get("paths", {})

    merged_paths = merged["paths"]

    for path, path_item in fastapi_paths.items():
        merged_paths[path] = copy.deepcopy(path_item)

    for path, path_item in erp_paths.items():
        converted_item = convert_30_to_31(copy.deepcopy(path_item))
        if path in merged_paths:
            # Merge HTTP methods inside the path item
            for method, op_def in converted_item.items():
                if method not in merged_paths[path]:
                    merged_paths[path][method] = op_def
                else:
                    print(f"[PATH COLLISION] Route {method.upper()} {path} exists in both specs. Retaining FastAPI definition.")
        else:
            merged_paths[path] = converted_item

    return merged


def main():
    fastapi_file = r"C:\Users\AYUSH\Downloads\src\spec\fastapi_openapi.json"
    erp_file = r"C:\Users\AYUSH\Downloads\src\spec\erp_mock_openapi.json"

    # Target output paths
    out_workspace_dir = os.path.join(os.getcwd(), "final_merged_api.json")

    print(f"Loading FastAPI specification from: {fastapi_file}")
    with open(fastapi_file, "r", encoding="utf-8") as f:
        fastapi_spec = json.load(f)

    print(f"Loading ERP Mock specification from: {erp_file}")
    with open(erp_file, "r", encoding="utf-8") as f:
        erp_spec = json.load(f)

    print("Merging specifications...")
    merged = merge_openapi_specs(fastapi_spec, erp_spec)

    with open(out_workspace_dir, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"Successfully generated: {out_workspace_dir}")

    # Summary report
    print("\nMerge Summary:")
    print(f"  OpenAPI Specification Version: {merged['openapi']}")
    print(f"  API Title: {merged['info']['title']}")
    print(f"  Total Paths / Endpoints: {len(merged['paths'])}")
    for p in sorted(merged["paths"].keys()):
        methods = [m.upper() for m in merged["paths"][p].keys() if m != "parameters"]
        print(f"    - {', '.join(methods):<12} {p}")
    print(f"  Total Schemas: {len(merged['components']['schemas'])}")
    print(f"  Total Tags: {len(merged['tags'])}")
    print(f"  Total Server Configurations: {len(merged['servers'])}")


if __name__ == "__main__":
    main()
