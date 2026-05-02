import os

def tail_file(filename, lines=50):
    try:
        with open(filename, "r") as f:
            lines_list = f.readlines()
            return f"--- {filename} ---\n" + "".join(lines_list[-lines:])
    except Exception as e:
        return f"--- {filename} ---\nError: {e}\n"

logs = [
    "/home/bamuskal/Documents/ai-super/data/logs/ai-orchestrator.log",
    "/home/bamuskal/Documents/ai-super/data/logs/startup.log",
    "/home/bamuskal/Documents/ai-super/data/logs/manual_restart.log",
    "/home/bamuskal/Documents/ai-super/data/logs/celery.log"
]

out = ""
for log in logs:
    out += tail_file(log) + "\n\n"

with open("/home/bamuskal/Documents/ai-super/log_tail.txt", "w") as f:
    f.write(out)
