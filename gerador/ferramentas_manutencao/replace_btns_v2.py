import os, re

html_dir = r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates"

# Allowed btn classes to keep (structural or icon-grow)
allowed_btn_classes = {"btn-icon-grow", "btn-close", "btn-group", "btn-group-sm", "btn-link"}

def replace_btn_classes(match):
    class_str = match.group(1)
    classes = class_str.split()
    new_classes = []
    has_btn = False
    
    for c in classes:
        # If it's `btn` or something like `btn-primary`, `btn-sm`, `btn-outline-danger`
        if c == "btn" or c.startswith("btn-"):
            if c in allowed_btn_classes:
                new_classes.append(c)
            else:
                has_btn = True
        else:
            # Keep other utility classes like `w-100`, `d-flex`, `shadow`, etc.
            new_classes.append(c)
            
    if has_btn and "btn-nft" not in new_classes:
        new_classes.insert(0, "btn-nft")
        
    return 'class="' + " ".join(new_classes) + '"'

for filename in os.listdir(html_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(html_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(r'class="([^"]*)"', replace_btn_classes, content)

        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filename}")
print("Done!")
