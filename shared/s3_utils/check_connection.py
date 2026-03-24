#!/usr/bin/env python3
"""
S3 Connection Diagnostic — run this BEFORE starting any agent.

Usage (from any agent directory):
    cd ~/vcsai/construction-intelligence-agent
    python ../s3_utils/check_connection.py

Or from PROD_SETUP root:
    python s3_utils/check_connection.py
"""

import os
import sys
import json
from pathlib import Path

# Add PROD_SETUP to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROD_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROD_ROOT))

print("=" * 70)
print("  S3 CONNECTION DIAGNOSTIC")
print("=" * 70)
print()

# Step 1: Check CWD and .env files
cwd = Path.cwd()
print(f"  CWD:        {cwd}")
print(f"  PROD_ROOT:  {PROD_ROOT}")
print()

# Step 2: Find .env files
print("  .env file search:")
env_files = []
for agent_dir in [
    cwd,
    PROD_ROOT / "construction-intelligence-agent",
    PROD_ROOT / "RAG_agent_VCS" / "RAG",
    PROD_ROOT / "SQL-Intelligence-Agent",
    PROD_ROOT / "INGESTION_for_RAG_agent",
    PROD_ROOT / "document-qa-agent",
]:
    env_file = agent_dir / ".env"
    exists = env_file.exists()
    print(f"    {env_file}: {'FOUND' if exists else 'NOT FOUND'}")
    if exists:
        env_files.append(env_file)

print()

# Step 3: Check what STORAGE_BACKEND is in each .env
print("  STORAGE_BACKEND values in .env files:")
for env_file in env_files:
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("STORAGE_BACKEND") and "=" in line:
                val = line.split("=", 1)[1].strip()
                print(f"    {env_file.parent.name}/.env: STORAGE_BACKEND={val!r}")
                break

print()

# Step 4: Check os.environ BEFORE loading .env
print("  os.environ (BEFORE dotenv load):")
for key in ["STORAGE_BACKEND", "S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "S3_AGENT_PREFIX"]:
    val = os.environ.get(key)
    if val is not None:
        display = val[:20] + "..." if len(val) > 20 else val
        print(f"    {key}={display!r}")
    else:
        print(f"    {key}=(NOT SET)")

print()

# Step 5: Load .env and check again
print("  Loading .env via dotenv...")
try:
    from dotenv import load_dotenv
    # Load from CWD first
    cwd_env = cwd / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env, override=True)
        print(f"    Loaded: {cwd_env}")
    else:
        # Try first found agent .env
        for ef in env_files:
            load_dotenv(ef, override=True)
            print(f"    Loaded: {ef}")
            break
except ImportError:
    print("    ERROR: python-dotenv not installed!")

print()
print("  os.environ (AFTER dotenv load):")
for key in ["STORAGE_BACKEND", "S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_AGENT_PREFIX", "S3_REGION"]:
    val = os.environ.get(key)
    if val is not None:
        if "SECRET" in key and val:
            display = val[:8] + "..."
        elif val:
            display = val[:30] + "..." if len(val) > 30 else val
        else:
            display = "(EMPTY STRING)"
        print(f"    {key}={display}")
    else:
        print(f"    {key}=(NOT SET)")

print()

# Step 6: Test s3_utils config
print("  s3_utils.config test:")
try:
    from s3_utils.config import get_s3_config, verify_s3_connection
    get_s3_config.cache_clear()

    result = verify_s3_connection()
    print(f"    env_loaded:     {result['env_loaded']}")
    print(f"    env_path:       {result.get('env_path', 'None')}")
    print(f"    storage_backend: {result['config']['storage_backend']!r}")
    print(f"    is_s3_enabled:  {result['config']['is_s3_enabled']}")
    print(f"    bucket_name:    {result['config']['bucket_name']}")
    print(f"    has_credentials: {result['config']['has_credentials']}")
    print(f"    access_key_id:  {result['config']['access_key_id']}")
    print(f"    agent_prefix:   {result['config']['agent_prefix']}")
    print()

    if result["connected"]:
        print("  RESULT: S3 CONNECTION SUCCESSFUL")
    else:
        print(f"  RESULT: S3 CONNECTION FAILED — {result['error']}")

except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
