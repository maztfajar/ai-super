import sys
sys.path.insert(0, '.')
from agents.executor import AgentExecutor

executor = AgentExecutor.__new__(AgentExecutor)

# Simulate bloated agent_msgs with thinking blocks
bloated_msgs = [
    {"role": "system", "content": "You are an AI assistant."},
    {"role": "user", "content": "Hello"},
]

# Add 15 fake assistant messages with <thinking> blocks
for i in range(15):
    bloated_msgs.append({
        "role": "assistant", 
        "content": f"<thinking>Long reasoning block {i} that should be removed...</thinking><response>Actual response {i}</response>"
    })
    bloated_msgs.append({
        "role": "tool",
        "content": f"Tool result {i}"
    })

print(f"Before pruning: {len(bloated_msgs)} messages")
total_chars_before = sum(len(str(m)) for m in bloated_msgs)
print(f"Before pruning: {total_chars_before} total characters")

# Run pruner
pruned = executor._prune_agent_messages(bloated_msgs)

print(f"After pruning: {len(pruned)} messages")
total_chars_after = sum(len(str(m)) for m in pruned)
print(f"After pruning: {total_chars_after} total characters")

reduction = ((total_chars_before - total_chars_after) / total_chars_before) * 100
print(f"📉 Context reduction: {reduction:.1f}%")

# Check thinking blocks are gone
has_thinking = any("<thinking>" in str(m) for m in pruned)
if not has_thinking:
    print("✅ All <thinking> blocks removed successfully")
else:
    print("❌ Some <thinking> blocks still remain!")

# Check message limit
if len(pruned) <= 22:
    print(f"✅ Message count within limit: {len(pruned)}")
else:
    print(f"❌ Too many messages: {len(pruned)}")
