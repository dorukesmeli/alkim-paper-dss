import json

log_file = "/Users/dorukesmeli/.gemini/antigravity/brain/949c777c-e48c-4a9a-8154-2341ee335925/.system_generated/logs/overview.txt"

app_lines = {}

with open(log_file, "r") as f:
    for line in f:
        try:
            data = json.loads(line)
            
            # Check for replace_file_content or view_file output that contains app.py lines
            # A view_file output might have lines like "1: line content"
            if "content" in data:
                text = data["content"]
            elif "output" in data:
                text = data["output"]
            elif "text" in data:
                text = data["text"]
            else:
                continue
                
            if "app.py" in text and "File Path:" in text:
                for t_line in text.split("\n"):
                    if t_line.split(":")[0].isdigit():
                        idx = int(t_line.split(":")[0])
                        val = ":".join(t_line.split(":")[1:])[1:]
                        if idx not in app_lines:
                            app_lines[idx] = val
        except:
            pass

print(f"Recovered {len(app_lines)} lines")

if len(app_lines) > 0:
    max_line = max(app_lines.keys())
    print(f"Max line: {max_line}")
    with open("app_recovered.py", "w") as f:
        for i in range(1, max_line + 1):
            f.write(app_lines.get(i, "") + "\n")
