import os, re

dirs = [r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates", r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"]

allowed_btn_classes = {"btn-icon-grow", "btn-close", "btn-group", "btn-group-sm", "btn-link"}

def replace_btn_classes(match):
    class_str = match.group(1)
    classes = class_str.split()
    new_classes = []
    has_btn = False
    
    for c in classes:
        if c == "btn" or c.startswith("btn-"):
            if c in allowed_btn_classes:
                new_classes.append(c)
            else:
                has_btn = True
        else:
            new_classes.append(c)
            
    if has_btn and "btn-nft" not in new_classes:
        new_classes.insert(0, "btn-nft")
        
    return 'class="' + " ".join(new_classes) + '"'

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = re.sub(r'class="([^"]*)"', replace_btn_classes, content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")
print("Done!")
