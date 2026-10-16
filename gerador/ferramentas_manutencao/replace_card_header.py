import os, re

dirs = [r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates", r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"]

def replace_card_header(match):
    class_str = match.group(1)
    classes = class_str.split()
    
    # We only process if 'card-header' is in the class list as a standalone word
    if 'card-header' not in classes:
        return match.group(0)
        
    new_classes = []
    has_text_color = False
    for c in classes:
        # Check if it is a text color class
        if c.startswith('text-'):
            if c != 'text-secondary':
                continue # Skip other text color classes to replace them
        new_classes.append(c)
        
    if 'text-secondary' not in new_classes:
        new_classes.append('text-secondary')
        
    return 'class="' + " ".join(new_classes) + '"'

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace class="..." attributes containing card-header
            new_content = re.sub(r'class="([^"]*card-header[^"]*)"', replace_card_header, content)
            new_content = re.sub(r"class='([^']*card-header[^']*)'", replace_card_header, new_content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")
print("Done!")
