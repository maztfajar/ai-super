import asyncio
import json
import structlog
from typing import List, Dict, Any
from core.model_manager import model_manager

log = structlog.get_logger()

VOTING_PROMPT = """You are the AI Orchestrator Voting Judge.
You have been provided with multiple responses from different AI models to the same user task.
Evaluate each response carefully and return the index of the absolute BEST response.

Your evaluation MUST be based on:
1. Accuracy (35%)
2. Relevance (25%)
3. Reasoning (25%)
4. Confidence & Clarity (15%)

Output ONLY valid JSON in this exact format:
{
    "winner_index": 0,
    "reasoning": "Model 0 had superior reasoning and correctly identified the edge case."
}
"""

class VotingEngine:
    async def execute_complex_task(self, system_prompt: str, user_message: str, history: list) -> str:
        voting_models = self._select_voting_models()
        if not voting_models:
            return "Error: No models available for voting."
            
        log.info(f"Initiating Multi-AI Parallel Voting with {len(voting_models)} models: {voting_models}")
        
        tasks = []
        for model in voting_models:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})
            # Generate responses in parallel
            tasks.append(model_manager.chat_completion(model, messages, temperature=0.7, max_tokens=2048))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                log.warning(f"Model {voting_models[i]} failed during voting", error=str(res))
            else:
                valid_responses.append({"model": voting_models[i], "response": str(res)})
                
        if not valid_responses:
            log.error("All voting models failed!")
            return "Error: Multi-AI Execution failed. All models threw exceptions."
            
        if len(valid_responses) == 1:
            log.info("Only one valid response returned. Skipping voting phase.")
            return f"**VOTING WINNER ({valid_responses[0]['model']})**\n\n{valid_responses[0]['response']}"
            
        # Compile responses for the Judge
        judge_prompt = "User Task:\n" + user_message + "\n\n---\n\nResponses to Evaluate:\n\n"
        for idx, item in enumerate(valid_responses):
            judge_prompt += f"### RESPONSE {idx} (from model hidden)\n{item['response']}\n\n"
            
        judge_messages = [
            {"role": "system", "content": VOTING_PROMPT},
            {"role": "user", "content": judge_prompt}
        ]
        
        judge_model = self._select_judge_model()
        log.info(f"Judging {len(valid_responses)} responses using {judge_model}...")
        
        try:
            judge_res = await model_manager.chat_completion(judge_model, judge_messages, temperature=0.2, max_tokens=500)
            
            # Extract JSON cleanly regardless of markdown format
            cleaned = judge_res
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
                
            data = json.loads(cleaned)
            winner_idx = data.get("winner_index", 0)
            reasoning = data.get("reasoning", "")
            
            if winner_idx < 0 or winner_idx >= len(valid_responses):
                winner_idx = 0
                
            winner = valid_responses[winner_idx]
            log.info(f"Voting complete! Winner: {winner['model']}. Reason: {reasoning}")
            
            # Mark the output clearly
            return f"**[Multi-AI Analysis Result]**\nVerified through parallel execution. Selected {winner['model']} as highest quality response.\n*Reasoning: {reasoning}*\n\n---\n\n{winner['response']}"
            
        except Exception as e:
            log.error("Judge failed to parse result, falling back to response 0", error=str(e))
            return f"**[Multi-AI Analysis Fallback]**\n\n{valid_responses[0]['response']}"

    def _select_voting_models(self) -> List[str]:
        # Gather all connected models
        available = list(model_manager.available_models.keys())
        if not available:
            return []
            
        # Prioritize smart/complex models for voting
        targets = ["gpt-4o", "claude-3-5-sonnet", "claude-3-opus", "gemini-1.5-pro", "seed-2-0-pro", "llama3.1"]
        selected = []
        
        for t in targets:
            for a in available:
                if t in a and a not in selected:
                    selected.append(a)
                    # Limit to max 3 parallel requests to prevent timeouts
                    if len(selected) >= 3:
                        return selected
                        
        # Fill rest with whatever is active
        for a in available:
            if a not in selected:
                selected.append(a)
            if len(selected) >= 3:
                break
                
        return selected

    def _select_judge_model(self) -> str:
        # GPT-4o or Sonnet make best judges
        best_judges = ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]
        for j in best_judges:
            for k in model_manager.available_models.keys():
                if j in k:
                    return k
        # Fallback to whatever
        return model_manager.get_default_model()

voting_engine = VotingEngine()
