import os
import re

dirs = [
    r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates",
    r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"
]

total_changes = 0

def clean_card_header(match):
    global total_changes
    class_str = match.group(1)
    tokens = class_str.split()
    if 'card-header' not in tokens:
        return match.group(0)
    
    # Remove any bg-* classes (e.g. bg-light, bg-white, bg-success-subtle, bg-danger, bg-warning, etc.)
    new_tokens = [t for t in tokens if not t.startswith('bg-')]
    
    if new_tokens != tokens:
        total_changes += 1
        return f'class="{" ".join(new_tokens)}"'
    return match.group(0)

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = re.sub(r'class="([^"]*card-header[^"]*)"', clean_card_header, content)
            new_content = re.sub(r"class='([^']*card-header[^']*)'", clean_card_header, new_content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")

print(f"Done! Cleaned bg classes from {total_changes} card-header elements.")
