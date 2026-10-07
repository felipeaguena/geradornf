import os
import re

dirs = [
    r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates",
    r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"
]

total_replaced = 0

def clean_class_str(class_str):
    # Split on whitespace preserving potential template tags or order
    tokens = class_str.split()
    # Check if both 'card' and 'border' exist as exact classes
    if 'card' in tokens and 'border' in tokens:
        # Remove 'card' and 'border'
        new_tokens = [t for t in tokens if t not in ('card', 'border')]
        return ' '.join(new_tokens), True
    return class_str, False

def replace_double_quotes(match):
    global total_replaced
    new_str, changed = clean_class_str(match.group(1))
    if changed:
        total_replaced += 1
        return f'class="{new_str}"'
    return match.group(0)

def replace_single_quotes(match):
    global total_replaced
    new_str, changed = clean_class_str(match.group(1))
    if changed:
        total_replaced += 1
        return f"class='{new_str}'"
    return match.group(0)

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = re.sub(r'class="([^"]*)"', replace_double_quotes, content)
            new_content = re.sub(r"class='([^']*)'", replace_single_quotes, new_content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")

print(f"Done! Replaced {total_replaced} class occurrences.")
