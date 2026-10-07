import os, re

dirs = [r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates", r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\static\js"]

def process_classes(class_str):
    # If the class string contains a template literal variable, we might need special handling.
    # But for simplicity, let's just use string replacement for common ones, or regex.
    pass

# Instead of parsing, we can just use regex to replace the class attribute entirely if it contains badge,
# but we need to keep non-color classes.

def replace_badge(match):
    class_str = match.group(1)
    
    # Check if 'badge' is a standalone word
    if not re.search(r'\bbadge\b', class_str):
        return match.group(0)
        
    # We will remove: bg-*, text-*, border, border-*, fw-*, and any ${...} dynamic variables
    # (since the dynamic ones usually supply colors)
    # Wait, if we remove ${...}, we might remove ${resumo.xml_construido ? 'bg-success' : 'bg-danger'}.
    # That is exactly what we want to remove, because now ALL badges are info.
    
    # Remove dynamic parts ${...}
    class_str = re.sub(r'\$\{.*?\}', '', class_str)
    
    classes = class_str.split()
    new_classes = []
    
    for c in classes:
        if c.startswith('bg-') or c.startswith('text-') or c.startswith('border-') or c.startswith('fw-') or c == 'border':
            continue
        new_classes.append(c)
        
    # Ensure badge is there (it should be)
    if 'badge' not in new_classes:
        new_classes.insert(0, 'badge')
        
    # Add the required standardized classes
    for required in ['bg-info-subtle', 'text-info', 'fw-bold']:
        if required not in new_classes:
            new_classes.append(required)
            
    return 'class="' + " ".join(new_classes) + '"'

for target_dir in dirs:
    for filename in os.listdir(target_dir):
        if filename.endswith(".html") or filename.endswith(".js"):
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = re.sub(r'class="([^"]*badge[^"]*)"', replace_badge, content)
            
            # For js files, sometimes they use single quotes: class='...'
            # Let's also do single quotes
            new_content = re.sub(r"class='([^']*badge[^']*)'", replace_badge, new_content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {filename}")
print("Done!")
