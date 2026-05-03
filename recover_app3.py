import json

log_file = "/Users/dorukesmeli/.gemini/antigravity/brain/949c777c-e48c-4a9a-8154-2341ee335925/.system_generated/logs/overview.txt"

with open(log_file, "r") as f:
    text = f.read()
    
# Let's search for "def page_analysis" in the raw text
idx = text.find("def page_analysis")
if idx != -1:
    print("Found page_analysis!")
    print(text[idx:idx+2000])
else:
    print("Not found in overview.txt")
