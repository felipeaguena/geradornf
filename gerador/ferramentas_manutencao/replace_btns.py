import os, re

html_dir = r"c:\Users\felipeaguena\Documents\XMLNFT\gerador\templates"
for filename in os.listdir(html_dir):
    if filename.endswith(".html"):
        filepath = os.path.join(html_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        def replace_btn_classes(match):
            class_str = match.group(1)
            classes = class_str.split()
            new_classes = []
            is_btn = False
            for c in classes:
                if c == "btn" or (c.startswith("btn-") and c not in ["btn-icon-grow", "btn-close", "btn-group"]):
                    is_btn = True
                else:
                    new_classes.append(c)
            
            if is_btn and "btn-nft" not in new_classes:
                new_classes.insert(0, "btn-nft")
                
            return "class=\"" + " ".join(new_classes) + "\""

        new_content = re.sub(r'class="([^"]*)"', replace_btn_classes, content)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
print("Done!")
