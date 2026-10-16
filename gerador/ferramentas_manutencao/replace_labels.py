import os, re

dirs = [r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates", r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"]

def replace_label_class(match):
    # match.group(0) is the entire `<label ... class="...">`
    # match.group(1) is the classes string
    class_str = match.group(1)
    
    if "text-primary" not in class_str.split():
        return match.group(0) # Do not modify if text-primary is not present as a distinct class
        
    # Standard classes required
    new_classes = "form-label small fw-bold mb-1"
    
    # We replace the class attribute with the new ones
    return f'class="{new_classes}"'

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Find <label ... class="...">
            # The regex handles label tags with a class attribute.
            # It replaces the class attribute.
            new_content = re.sub(r'<label\b[^>]*?class="([^"]*text-primary[^"]*)"', lambda m: m.group(0).replace(f'class="{m.group(1)}"', replace_label_class(m)), content)

            # Let's write a simpler regex for just the class replacement inside <label>
            # Actually, doing it via a function matching the whole tag is better:
            def replace_tag(m):
                tag = m.group(0)
                class_match = re.search(r'class="([^"]+)"', tag)
                if class_match:
                    classes = class_match.group(1).split()
                    if "text-primary" in classes:
                        # Rebuild tag replacing class="..."
                        new_tag = tag.replace(class_match.group(0), 'class="form-label small fw-bold mb-1"')
                        return new_tag
                return tag

            new_content = re.sub(r'<label\b[^>]*>', replace_tag, content)


            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")
print("Done!")
