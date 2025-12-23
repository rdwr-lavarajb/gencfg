"""
Setup script for Phase 2 environment configuration
"""

import os
from pathlib import Path


def setup_env():
    """Guide user through environment setup"""
    
    print("=" * 70)
    print("Phase 2 Environment Setup")
    print("=" * 70)
    print()
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    # Check if .env already exists
    if env_file.exists():
        print("✅ .env file already exists")
        
        # Check if API key is set
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('OPENAI_API_KEY')
            
            if api_key and api_key != 'your-openai-api-key-here':
                print("✅ OPENAI_API_KEY is configured")
                print()
                print("Your environment is ready for Phase 2!")
            else:
                print("⚠️  OPENAI_API_KEY not set in .env file")
                print()
                print("Please edit .env and add your OpenAI API key:")
                print(f"   {env_file.absolute()}")
                print()
                print("Get your API key from: https://platform.openai.com/api-keys")
        except ImportError:
            print("⚠️  python-dotenv not installed")
            print("   Install it with: pip install python-dotenv")
            print("   Or the .env file won't be automatically loaded")
    else:
        print("📝 Creating .env file from template...")
        
        if env_example.exists():
            # Copy .env.example to .env
            with open(env_example, 'r') as f:
                content = f.read()
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Created .env file: {env_file.absolute()}")
            print()
            print("⚠️  IMPORTANT: Edit .env and add your OpenAI API key")
            print()
            print("Steps:")
            print("1. Get your API key from: https://platform.openai.com/api-keys")
            print(f"2. Edit: {env_file.absolute()}")
            print("3. Replace 'your-openai-api-key-here' with your actual key")
            print("4. Save the file")
            print()
            print("Example .env content:")
            print("   OPENAI_API_KEY=sk-proj-abc123...")
        else:
            print("❌ .env.example not found")
    
    print()
    print("=" * 70)
    print()
    
    # Test if we can import required packages
    print("Checking dependencies...")
    try:
        import openai
        print("✅ openai package installed")
    except ImportError:
        print("❌ openai package not installed")
        print("   Run: pip install -r requirements.txt")
    
    try:
        import dotenv
        print("✅ python-dotenv package installed")
    except ImportError:
        print("❌ python-dotenv package not installed")
        print("   Run: pip install -r requirements.txt")
    
    print()


if __name__ == "__main__":
    setup_env()
