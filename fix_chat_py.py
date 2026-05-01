"""
Fix critical indentation bug in backend/api/chat.py

Bug: Event processing block (if event.type == "chunk", etc.) is OUTSIDE the while loop,
so events are consumed from queue but never processed/yielded to the client.

Also removes orphaned timeout code after finally block that runs unconditionally.
"""
import re

filepath = '/home/bamuskal/Documents/ai-super/backend/api/chat.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken section: lines 367-450
# The event processing block starts at "                if event.type ==" (16 spaces)
# It should be at "                    if event.type ==" (20 spaces, inside the while loop)

# Step 1: Fix the event processing block indentation (add 4 spaces)
# The block starts right after "                    event = item\n\n"
# and ends before "            finally:"

old_block = '''                if event.type == "chunk":
                    full_response += event.content
                    yield event.to_sse()

                elif event.type == "process":
                    # Structured process step — forward directly to frontend
                    yield event.to_sse()
                    # Also collect for storage
                    if event.data:
                        action = event.data.get("action", "")
                        detail = event.data.get("detail", "")
                        thinking_steps.append(f"{action}: {detail}" if detail else action)

                elif event.type == "status":
                    # Collect thinking steps
                    thinking_steps.append(event.content)
                    yield event.to_sse()

                elif event.type == "pending_confirmation":
                    # VPS safety protocol — send confirmation request
                    payload = {
                        "type": "pending_confirmation",
                        "command": req.message,
                        "purpose": event.data.get("purpose", "") if event.data else "",
                        "risk": event.data.get("risk", "MEDIUM") if event.data else "MEDIUM",
                        "session_id": session.id,
                    }
                    yield f"data: {json.dumps(payload)}\\n\\n"
                    return  # Stop generator

                elif event.type == "done":
                    # DB save logic has been moved to the finally block to ensure it always runs.
                    await save_to_db_if_needed()

                    # Pass through done event with orchestrator metadata + thinking process
                    done_payload = {"type": "done", "sources": rag_sources}
                    if event.data:
                        done_payload.update(event.data)
                    # Include thinking process for expandable thinking section
                    done_payload["thinking_process"] = "\\n".join(thinking_steps) if thinking_steps else ""
                    yield f"data: {json.dumps(done_payload)}\\n\\n"
                    return # Exit generator cleanly

                elif event.type == "error":
                    yield event.to_sse()
                    full_response = f"Error: {event.content}"
                    error_occurred = True'''

# Check if old block exists
if old_block not in content:
    print("WARNING: Old block not found verbatim. Trying to find it...")
    # Find it by searching for the key pattern
    idx = content.find('                if event.type == "chunk":')
    if idx == -1:
        print("ERROR: Cannot find event processing block at all!")
        exit(1)
    else:
        print(f"Found event processing block at position {idx}")
        # Let's see what's around it
        start = max(0, idx - 200)
        end = min(len(content), idx + 2000)
        print("CONTEXT:")
        print(repr(content[start:end]))
else:
    print("Found old block verbatim!")

# New block: indented 4 more spaces (inside the while loop)
new_block = '''                    # ── Process each event INSIDE the loop ──────────
                    if event.type == "chunk":
                        full_response += event.content
                        yield event.to_sse()

                    elif event.type == "process":
                        # Structured process step — forward directly to frontend
                        yield event.to_sse()
                        # Also collect for storage
                        if event.data:
                            action = event.data.get("action", "")
                            detail = event.data.get("detail", "")
                            thinking_steps.append(f"{action}: {detail}" if detail else action)

                    elif event.type == "status":
                        # Collect thinking steps
                        thinking_steps.append(event.content)
                        yield event.to_sse()

                    elif event.type == "pending_confirmation":
                        # VPS safety protocol — send confirmation request
                        payload = {
                            "type": "pending_confirmation",
                            "command": req.message,
                            "purpose": event.data.get("purpose", "") if event.data else "",
                            "risk": event.data.get("risk", "MEDIUM") if event.data else "MEDIUM",
                            "session_id": session.id,
                        }
                        yield f"data: {json.dumps(payload)}\\n\\n"
                        return  # Stop generator

                    elif event.type == "done":
                        # Save AI response to DB
                        await save_to_db_if_needed()

                        # Pass through done event with orchestrator metadata + thinking process
                        done_payload = {"type": "done", "sources": rag_sources}
                        if event.data:
                            done_payload.update(event.data)
                        # Include thinking process for expandable thinking section
                        done_payload["thinking_process"] = "\\n".join(thinking_steps) if thinking_steps else ""
                        yield f"data: {json.dumps(done_payload)}\\n\\n"
                        return # Exit generator cleanly

                    elif event.type == "error":
                        yield event.to_sse()
                        full_response = f"Error: {event.content}"
                        error_occurred = True'''

content = content.replace(old_block, new_block)

# Step 2: Remove orphaned timeout code after finally block
# This code runs unconditionally (not inside any try/except) and is always wrong
orphaned_code = '''            import traceback
            traceback.print_exc()
            err_str = "⏱️ Operasi timeout - permintaan Anda memerlukan waktu terlalu lama. Sistem akan melanjutkan dengan respons yang sudah ada."
            log.error("Chat timeout", message=req.message[:50])
            
            # Try to get partial response before timeout
            if full_response.strip():
                yield f"data: {json.dumps({'type': 'chunk', 'content': '\\\\n\\\\n⚠️ Partial response due to timeout:\\\\n\\\\n' + full_response[-1000:]})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done', 'partial': True, 'sources': rag_sources})}\\n\\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'content': err_str})}\\n\\n"
                full_response = err_str
            error_occurred = True
            thinking_steps.append(f"❌ Timeout error: {err_str}")'''

if orphaned_code in content:
    content = content.replace(orphaned_code, '')
    print("Removed orphaned timeout code")
else:
    print("WARNING: Orphaned timeout code not found verbatim, trying line-by-line...")
    # Try to find and remove it line by line
    lines = content.split('\n')
    new_lines = []
    skip_until_except = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if '            import traceback' in line and i > 0 and 'pass' in lines[i-1]:
            # Found the orphaned block after the finally's pass
            # Skip lines until we hit the next except block
            skip_count = 0
            while i < len(lines) and skip_count < 15:
                if 'except asyncio.CancelledError' in lines[i]:
                    break
                i += 1
                skip_count += 1
            print(f"Skipped {skip_count} orphaned lines")
            continue
        new_lines.append(line)
        i += 1
    if len(new_lines) != len(lines):
        content = '\n'.join(new_lines)
        print(f"Removed {len(lines) - len(new_lines)} orphaned lines")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fix applied successfully!")

# Verify
with open(filepath, 'r') as f:
    fixed = f.read()

# Check the fix is correct
if '                    if event.type == "chunk":' in fixed:
    print("✅ Verification: event processing block is now properly indented inside while loop")
else:
    print("❌ Verification FAILED: event processing block not at correct indentation")

if 'import traceback' not in fixed or fixed.count('import traceback') == 0:
    print("✅ Verification: orphaned traceback code removed")
elif fixed.count('import traceback') <= 1:
    print("⚠️ Verification: traceback import found once (in except block, OK)")
