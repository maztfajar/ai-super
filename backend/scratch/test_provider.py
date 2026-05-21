import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.model_manager import model_manager
print(model_manager._get_provider("pollinations/flux"))
