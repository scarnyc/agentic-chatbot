#!/usr/bin/env python3
"""Test script for file upload functionality."""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, '/Users/scar_nyc/Documents/GitHub/agentic-supervisor-flow/agentic-workflow')

def test_imports():
    """Test if all required imports work."""
    try:
        # Test basic imports
        print("Testing basic imports...")
        import json
        import base64
        print("✅ Basic imports successful")
        
        # Test FastAPI imports
        print("Testing FastAPI imports...")
        from fastapi import FastAPI, UploadFile, File, Form
        print("✅ FastAPI imports successful")
        
        # Test PIL import
        print("Testing PIL import...")
        from PIL import Image
        print("✅ PIL import successful")
        
        # Test unified multimodal tools
        print("Testing multimodal tools...")
        from tools.unified_multimodal_tools import analyze_image_and_store, store_text_memory
        print("✅ Multimodal tools import successful")
        
        print("\n🎉 All imports successful! Upload functionality should work.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_imports()