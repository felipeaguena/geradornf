import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """    key_info = ET.SubElement(sig, f'{{{DS_NS}}}KeyInfo')
    x509_data = ET.SubElement(key_info, f'{{{DS_NS}}}X509Data')
    x509_cert = ET.SubElement(x509_data, f'{{{DS_NS}}}X509Certificate')
    x509_cert.text = cert_str

    # Omitimos o KeyInfo e X509Certificate propositalmente"""

content = re.sub(r'# Omitimos o KeyInfo e X509Certificate propositalmente', replacement, content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
