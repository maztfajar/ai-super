import json
import asyncio
from typing import AsyncGenerator
import structlog
from core.model_manager import model_manager
from core.smart_router import smart_router
from agents.tools import execute_bash, read_file, write_file, ask_model

log = structlog.get_logger()

def build_agent_system_prompt(current_model: str) -> str:
    from core.model_manager import model_manager
    models = list(model_manager.available_models.keys())
    model_list_str = ", ".join(models)
    
    return f"""You are AI SUPER ASSISTANT AI, a Super Assistant autonomous agent currently running as '{current_model}'.
You can use tools to perform tasks on the local system and orchestrate other AI models.

**CORE DIRECTIVE**: You are part of an advanced AI orchestration system. When you receive a complex project or request, you MUST collaborate with other AI models in the system to gather different perspectives, verify logic, or sub-contract tasks. You operate in the background until the final, verified conclusion is reached.

Currently available tools:
1. `execute_bash` - Run a bash command. Arguments: `command` (string).
2. `read_file` - Read contents of a file. Arguments: `path` (string).
3. `write_file` - Write content to a file. Arguments: `path` (string), `content` (string).
4. `ask_model` - Ask another AI model to perform a specific sub-task or get its perspective. Arguments: `model_id` (string), `prompt` (string). Available models in the system: {model_list_str}.

**TOOL USAGE RULES:**
- If you need to use a tool, you MUST output ONLY the exact JSON tool format below and NOTHING ELSE. DO NOT output any conversational text or "thinking" before the tool call.
- Tool Format (must be on a new line):
  <tool>{{"name": "tool_name", "args": {{"arg_name": "value"}}}}</tool>
- Immediately STOP generating after the <tool> block.
- You will receive the tool's result in an <observation> block.

Once you have gathered enough information and cross-checked with other models (if necessary), output your **FINAL ANSWER**. This final answer will be shown directly to the user. Do format your final answer nicely using Markdown. Do NOT use tool blocks in your final answer.
"""

class AgentExecutor:
    async def stream_chat(
        self,
        base_model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        include_tool_logs: bool = True,
    ) -> AsyncGenerator[str, None]:
        
        system_prompt = build_agent_system_prompt(base_model)
        
        # Inject our agent system prompt
        agent_msgs = list(messages)
        has_system = False
        for m in agent_msgs:
            if m["role"] == "system":
                m["content"] += f"\n\n{system_prompt}"
                has_system = True
                break
        if not has_system:
            agent_msgs.insert(0, {"role": "system", "content": system_prompt})
            
        MAX_ITERATIONS = 8
        final_buffer = ""
        
        for iteration in range(MAX_ITERATIONS):
            buffer = ""
            has_tool_started = False
            flushed_buffer = False
            
            async for chunk in model_manager.chat_stream(base_model, agent_msgs, temperature, max_tokens):
                buffer += chunk
                
                if "<tool>" in buffer:
                    has_tool_started = True
                
                if has_tool_started:
                    if "</tool>" in buffer:
                        break
                    continue
                
                # Wait to determine if it's forming a <tool> block
                clean_buf = buffer.lstrip()
                if not clean_buf:
                    continue
                    
                if clean_buf.startswith("<"):
                    if len(clean_buf) < 7:
                        continue
                
                if not flushed_buffer:
                    yield buffer
                    flushed_buffer = True
                else:
                    yield chunk
            
            final_buffer += buffer
            
            # Periksa jika model berniat menggunakan tool (mengandung <tool>)
            has_tool = "<tool>" in buffer
            if has_tool and "</tool>" not in buffer:
                buffer += "</tool>"  # Paksa tutup jika kepotong/model lupa
                
            if has_tool:
                try:
                    tool_content = buffer.split("<tool>")[1].split("</tool>")[0].strip()
                    
                    # Bersihkan jika LLM memasukkan markdown json
                    if tool_content.startswith("```json"):
                        tool_content = tool_content[7:]
                    elif tool_content.startswith("```"):
                        tool_content = tool_content[3:]
                    if tool_content.endswith("```"):
                        tool_content = tool_content[:-3]
                        
                    tool_content = tool_content.strip()
                    tool_req = json.loads(tool_content)
                    
                    cmd = tool_req.get("name")
                    args = tool_req.get("args", {})
                    
                    # Yield explicitly — wrap in <details> for browser if requested
                    if include_tool_logs:
                        yield f'\n\n<details class="tool-log">\n<summary><span>⚙️ **Executing {cmd}...**</span> <span class="toggle-icon">▼</span></summary>\n\n'
                        
                        res = ""
                        if cmd == "execute_bash":
                            res = await execute_bash(args.get("command", ""))
                        elif cmd == "read_file":
                            res = await read_file(args.get("path", ""))
                        elif cmd == "write_file":
                            res = await write_file(args.get("path", ""), args.get("content", ""))
                        elif cmd == "ask_model":
                            res = await ask_model(args.get("model_id", ""), args.get("prompt", ""))
                        else:
                            res = f"Unknown tool: {cmd}"
                            
                        obs_text = f"\n<observation>\n{res}\n</observation>\n"
                        
                        yield f"**Result:**\n```\n{res[:1500]}{'...' if len(res)>1500 else ''}\n```\n\n</details>\n\n"
                    else:
                        # Di platform yang tidak support HTML/Details (Telegram/WA), sembunyikan total
                        # Kecuali mungkin indikator kecil
                        res = ""
                        if cmd == "execute_bash":
                            res = await execute_bash(args.get("command", ""))
                        elif cmd == "read_file":
                            res = await read_file(args.get("path", ""))
                        elif cmd == "write_file":
                            res = await write_file(args.get("path", ""), args.get("content", ""))
                        elif cmd == "ask_model":
                            res = await ask_model(args.get("model_id", ""), args.get("prompt", ""))
                        else:
                            res = f"Unknown tool: {cmd}"
                        
                        obs_text = f"\n<observation>\n{res}\n</observation>\n"
                    
                    # Set history properly
                    agent_msgs.append({"role": "assistant", "content": buffer.split("<tool>")[0] + f"<tool>{tool_content}</tool>"})
                    agent_msgs.append({"role": "user", "content": obs_text})
                    
                except Exception as e:
                    if include_tool_logs:
                        yield f"\n> ❌ **Tool Error:** {str(e)}\n"
                    err_obs = f"\n<observation>\nError parsing or executing tool: {str(e)}\n</observation>\n"
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({"role": "user", "content": err_obs})
            else:
                # No tool call => Final answer reached
                break

agent_executor = AgentExecutor()
