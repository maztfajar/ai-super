import json
import structlog
from typing import Dict, Any
from core.model_manager import model_manager

log = structlog.get_logger()

CLASSIFIER_PROMPT = """You are the AI Orchestrator Core Task Classifier.
Read the user's request and classify it exactly into one of the following categories:
- SYSTEM: Managing the VPS, installing apps, checking system metrics (like htop, RAM, disk space), or running terminal commands (except simple git reads/writes).
- CODING: Asking to write, debug, explain, or refactor code.
- ANALYSIS: Complex reasoning, math, data extraction, complex planning, or summarizing large context.
- FILE OPERATION: Requests to create, edit, delete, or read a file on the local filesystem.
- GENERAL: Simple greetings, casual chat, simple factual questions, or anything that doesn't fit the above.

You must also determine if this task is 'is_complex'.
- is_complex = true IF it's CODING, ANALYSIS, or requires deep reasoning where considering multiple perspectives (multiple AIs) would be beneficial.
- is_complex = false IF it's GENERAL, simple SYSTEM/FILE commands, or direct factual questions.

Output ONLY valid JSON in this exact format:
{
    "category": "SYSTEM",
    "is_complex": false,
    "reasoning": "checking system RAM is a system task but not complex"
}
"""

class TaskClassifier:
    async def classify(self, message: str) -> Dict[str, Any]:
        # Gunakan model tercepat yang tersedia untuk klasifikasi
        fast_model = self._get_fast_model()
        messages = [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": f"User Request:\n{message}"}
        ]
        
        try:
            log.info("Classifying task", model=fast_model)
            result_str = await model_manager.chat_completion(
                model=fast_model,
                messages=messages,
                temperature=0.1,  # Strict JSON
                max_tokens=200
            )
            
            # Extract JSON block
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
                
            data = json.loads(result_str)
            return {
                "category": data.get("category", "GENERAL"),
                "is_complex": data.get("is_complex", False),
                "reasoning": data.get("reasoning", "")
            }
        except Exception as e:
            log.error("Classifier error, fallback to GENERAL to prevent blockers", error=str(e))
            return {"category": "GENERAL", "is_complex": False, "reasoning": "fallback due to error"}

    def _get_fast_model(self) -> str:
        # Prioritize really fast models for classification to reduce wait times
        priorities = ["gpt-5-nano", "gemini-2.5-flash-lite", "claude-haiku-4-5", "qwen3.6-flash"]
        
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()

task_classifier = TaskClassifier()
