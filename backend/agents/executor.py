import json
import re
import asyncio
from typing import AsyncGenerator
import structlog
from core.model_manager import model_manager
from core.smart_router import smart_router
from agents.tools import execute_bash, read_file, write_file, ask_model
from agents.tools.web_search import web_search

log = structlog.get_logger()

def build_agent_system_prompt(current_model: str) -> str:
    from core.model_manager import model_manager
    import datetime
    models = list(model_manager.available_models.keys())
    model_list_str = ", ".join(models)
    
    # Get current datetime to prevent models from rejecting future dates (e.g., cutoff in 2023 but current is 2026)
    current_time = datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")
    
    return f"""You are AI SUPER ASSISTANT, an advanced autonomous agent currently running as '{current_model}'.
CURRENT SYSTEM TIME: {current_time}. You MUST accept this as the true current date and time. Do NOT rely on your training cutoff date.

**INTERNET ACCESS:**
You have FULL and UNRESTRICTED live internet access via the `web_search` tool. 
If a user asks for news, recent events, or information beyond your training data, you MUST use `web_search` to find it. NEVER apologize or claim you don't have internet access. If you don't know, search the web like a human would.

**ABSOLUTE RULE — OUTPUT FORMAT:**
You MUST wrap your entire output in EXACTLY these XML tags. NO EXCEPTIONS.

Step 1 (HIDDEN from user): Put ALL your reasoning, analysis, and tool calls inside:
<thinking>
...your internal analysis, tool calls, etc...
</thinking>

Step 2 (SHOWN to user): Put ONLY your final answer inside:
<response>
...direct answer to user, formatted in Markdown...
</response>

CRITICAL: Do NOT write ANY text outside of these two tags. The system will BLOCK everything that is not inside <response> tags. If you write text without tags, the user sees NOTHING.

Available tools (use INSIDE <thinking> only):
1. execute_bash — run a command. Args: command (string).
2. read_file — read a file. Args: path (string).
3. write_file — write a file. Args: path (string), content (string).
4. ask_model — ask another AI for data processing or structural tasks. NEVER use this for factual/world knowledge queries. Args: model_id (string), prompt (string). Models: {model_list_str}.
5. web_search — search the web. MUST be used for real-world facts, news, and specific local information. Args: query (string).

Tool format (inside <thinking>):
<tool>{{"name": "tool_name", "args": {{"key": "value"}}}}</tool>
Stop generating immediately after a <tool> block. You will get results in <observation>.

Example for a simple greeting:
<thinking>
Simple greeting, no tools needed.
</thinking>
<response>
Hai! 👋 Ada yang bisa saya bantu?
</response>

Example for a system check:
<thinking>
User wants RAM info. I need to run a command.
<tool>{{"name": "execute_bash", "args": {{"command": "free -h"}}}}</tool>
</thinking>
[receives observation]
<response>
**RAM Server:**
- Total: 4 GB
- Used: 1.8 GB (45%)
- Free: 2.2 GB
</response>
"""


class ResponseFilter:
    """
    TagRewriter/Filter.
    Wraps <thinking> blocks into <details> dropdowns.
    Only emits content from <response> naturally or inside the <details> wrapper.
    Drops plain text outside of known tags.
    """
    def __init__(self):
        self.state = "WAITING"
        self.pending = ""
        self.ever_emitted = False

    def process(self, chunk: str) -> str:
        self.pending += chunk
        output = ""

        while self.pending:
            if self.state == "WAITING":
                # Look for earliest supported tag
                i_think = self.pending.find("<thinking>")
                i_resp = self.pending.find("<response>")
                i_tool = self.pending.find("<tool>")

                tags = []
                if i_think != -1: tags.append((i_think, "<thinking>"))
                if i_resp != -1: tags.append((i_resp, "<response>"))
                if i_tool != -1: tags.append((i_tool, "<tool>"))

                if tags:
                    tags.sort(key=lambda x: x[0])
                    idx, tag = tags[0]
                    # Discard anything before the earliest tag
                    self.pending = self.pending[idx:]
                    if tag == "<thinking>":
                        output += '\n\n<details class="tool-log" style="opacity: 0.8; font-size: 0.9em;"><summary><span>🤔 **Proses Berpikir...**</span> <span class="toggle-icon">▼</span></summary>\n\n'
                        self.pending = self.pending[len("<thinking>"):]
                        self.state = "THINKING"
                    elif tag == "<response>":
                        self.pending = self.pending[len("<response>"):]
                        self.state = "RESPONSE"
                        self.ever_emitted = True
                    elif tag == "<tool>":
                        # Handled by AgentExecutor outer loop
                        break
                else:
                    if len(self.pending) > 15:
                        self.pending = self.pending[-15:]
                    break

            elif self.state == "THINKING":
                end_think = self.pending.find("</thinking>")
                idx_tool = self.pending.find("<tool>")
                
                # If <tool> is found before </thinking>, let AgentExecutor grab it
                if idx_tool != -1 and (end_think == -1 or idx_tool < end_think):
                    output += self.pending[:idx_tool]
                    self.pending = self.pending[idx_tool:]
                    break
                
                if end_think != -1:
                    output += self.pending[:end_think]
                    output += '\n\n</details>\n\n'
                    self.pending = self.pending[end_think + len("</thinking>"):]
                    self.state = "WAITING"
                else:
                    safe = len(self.pending) - 15
                    if safe > 0:
                        output += self.pending[:safe]
                        self.pending = self.pending[safe:]
                    break

            elif self.state == "RESPONSE":
                end_resp = self.pending.find("</response>")
                idx_tool = self.pending.find("<tool>")
                
                if idx_tool != -1 and (end_resp == -1 or idx_tool < end_resp):
                    output += self.pending[:idx_tool]
                    self.pending = self.pending[idx_tool:]
                    break
                    
                if end_resp != -1:
                    output += self.pending[:end_resp]
                    self.pending = self.pending[end_resp + len("</response>"):]
                    self.state = "WAITING"
                else:
                    safe = len(self.pending) - 15
                    if safe > 0:
                        output += self.pending[:safe]
                        self.pending = self.pending[safe:]
                    break

        return output

    def flush(self) -> str:
        if self.state == "THINKING" and self.pending:
            res = self.pending + '\n\n</details>\n\n'
            self.pending = ""
            return res
        elif self.state == "RESPONSE" and self.pending:
            res = self.pending
            self.pending = ""
            return res
        return ""


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
        response_filter = ResponseFilter()
        
        for iteration in range(MAX_ITERATIONS):
            buffer = ""
            has_tool_started = False
            pre_tool_fed = False
            
            async for chunk in model_manager.chat_stream(base_model, agent_msgs, temperature, max_tokens):
                buffer += chunk
                
                if "<tool>" in buffer and not has_tool_started:
                    has_tool_started = True
                    # Feed everything before <tool> through the filter to cleanly emit into DOM
                    if not pre_tool_fed:
                        pre_tool_idx = buffer.find("<tool>")
                        pre_tool_text = buffer[:pre_tool_idx]
                        if pre_tool_text:
                            filtered = response_filter.process(pre_tool_text)
                            if filtered:
                                yield filtered
                                
                        # Auto-close <details> logic if interrupted during THINKING
                        if response_filter.state == "THINKING":
                            yield "\n\n</details>\n\n"
                            
                        pre_tool_fed = True
                        # Reset filter to prevent layout corruption
                        response_filter.state = "WAITING"
                        response_filter.pending = ""
                
                if has_tool_started:
                    if "</tool>" in buffer:
                        break
                    continue
                
                # Feed every chunk through the response filter
                filtered = response_filter.process(chunk)
                if filtered:
                    yield filtered
            
            # Check if model intends to use a tool
            has_tool = "<tool>" in buffer
            if has_tool and "</tool>" not in buffer:
                buffer += "</tool>"
                
            if has_tool:
                try:
                    tool_content = buffer.split("<tool>")[1].split("</tool>")[0].strip()
                    
                    # Clean markdown code blocks
                    clean_content = tool_content
                    if clean_content.startswith("```json"):
                        clean_content = clean_content[7:]
                    elif clean_content.startswith("```"):
                        clean_content = clean_content[3:]
                    if clean_content.endswith("```"):
                        clean_content = clean_content[:-3]
                    
                    clean_content = clean_content.strip()
                    
                    # Robust parsing: try json.loads first, then regex for first {...} block
                    tool_req = None
                    try:
                        tool_req = json.loads(clean_content)
                    except json.JSONDecodeError:
                        match = re.search(r'\{.*\}', clean_content, re.DOTALL)
                        if match:
                            try:
                                tool_req = json.loads(match.group(0))
                            except json.JSONDecodeError as e:
                                raise Exception(f"Failed to parse inner JSON: {e}. Raw: {clean_content}")
                        else:
                            raise Exception(f"No JSON object found in tool format: {clean_content}")
                    
                    cmd = tool_req.get("name")
                    args = tool_req.get("args", {})
                    
                    # Execute tool
                    res = ""
                    if cmd == "execute_bash":
                        res = await execute_bash(args.get("command", ""))
                    elif cmd == "read_file":
                        res = await read_file(args.get("path", ""))
                    elif cmd == "write_file":
                        res = await write_file(args.get("path", ""), args.get("content", ""))
                    elif cmd == "ask_model":
                        res = await ask_model(args.get("model_id", ""), args.get("prompt", ""))
                    elif cmd == "web_search":
                        res = await web_search(args.get("query", ""))
                    else:
                        res = f"Unknown tool: {cmd}"
                    
                    if include_tool_logs:
                        yield f'\n\n<details class="tool-log">\n<summary><span>⚙️ **Executing {cmd}...**</span> <span class="toggle-icon">▼</span></summary>\n\n'
                        yield f"**Result:**\n```\n{res[:1500]}{'...' if len(res)>1500 else ''}\n```\n\n</details>\n\n"
                            
                    obs_text = f"\n<observation>\n{res}\n</observation>\n"
                    
                    # Only store the tool call in history, without the pre-tool thinking text
                    agent_msgs.append({"role": "assistant", "content": f"<tool>{tool_content}</tool>"})
                    agent_msgs.append({"role": "user", "content": obs_text})
                    
                except Exception as e:
                    if include_tool_logs:
                        yield f"\n> ❌ **Tool Error:** {str(e)}\n"
                    err_obs = f"\n<observation>\nError parsing or executing tool: {str(e)}\n</observation>\n"
                    agent_msgs.append({"role": "assistant", "content": buffer})
                    agent_msgs.append({"role": "user", "content": err_obs})
            else:
                # No tool call => stream ended
                # Flush any remaining content in the filter
                remaining = response_filter.flush()
                if remaining:
                    yield remaining
                
                # SAFE FALLBACK: If the model never used <response> tags,
                # salvage the raw text. We strictly use `buffer` (which only contains 
                # the final iteration's output).
                if not response_filter.ever_emitted:
                    # Explicitly remove the entire <thinking> block and its contents first
                    fallback_text = re.sub(r'<thinking>.*?</thinking>', '', buffer, flags=re.DOTALL)
                    # Remove any loose tags remaining
                    fallback_text = re.sub(r'</?(?:thinking|response|tool|observation)>', '', fallback_text).strip()
                    if fallback_text:
                        yield fallback_text
                
                break

agent_executor = AgentExecutor()


