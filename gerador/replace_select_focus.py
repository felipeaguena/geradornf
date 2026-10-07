import re

with open('static/css/nft-theme.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Light mode replacement
old_light = """.form-control:focus,
.form-select:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(237, 90, 36, 0.2) !important;
  outline: none !important;
}"""

new_light = """.form-control:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(237, 90, 36, 0.2) !important;
  outline: none !important;
}
.form-select:focus {
  border-color: #8FFD05 !important;
  box-shadow: 0 0 0 3px rgba(143, 253, 5, 0.2) !important;
  outline: none !important;
}"""

content = content.replace(old_light, new_light)

# Dark mode replacement
old_dark = """.dark .form-control:focus,
[data-theme="dark"] .form-control:focus,
.dark .form-select:focus,
[data-theme="dark"] .form-select:focus {
  background-color: #171b26 !important;
  border-color: var(--primary) !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 3px rgba(237, 90, 36, 0.25) !important;
}"""

new_dark = """.dark .form-control:focus,
[data-theme="dark"] .form-control:focus {
  background-color: #171b26 !important;
  border-color: var(--primary) !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 3px rgba(237, 90, 36, 0.25) !important;
}
.dark .form-select:focus,
[data-theme="dark"] .form-select:focus {
  background-color: #171b26 !important;
  border-color: #8FFD05 !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 3px rgba(143, 253, 5, 0.25) !important;
}"""

content = content.replace(old_dark, new_dark)

with open('static/css/nft-theme.css', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
