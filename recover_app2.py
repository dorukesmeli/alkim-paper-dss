import json

log_file = "/Users/dorukesmeli/.gemini/antigravity/brain/949c777c-e48c-4a9a-8154-2341ee335925/.system_generated/logs/overview.txt"

app_lines = {}

with open(log_file, "r") as f:
    text = f.read()
    
# Use regex to find lines
import re
matches = re.findall(r'^(\d+):\s(.*)$', text, re.MULTILINE)
for num, content in matches:
    try:
        app_lines[int(num)] = content
    except:
        pass

print(f"Recovered {len(app_lines)} lines")

if len(app_lines) > 0:
    max_line = max(app_lines.keys())
    print(f"Max line: {max_line}")
    with open("app_recovered.py", "w") as f:
        for i in range(1, max_line + 1):
            f.write(app_lines.get(i, "") + "\n")
