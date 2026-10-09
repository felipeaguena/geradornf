with open('test_out.txt', 'w', encoding='utf-8') as out:
    pass

import test_clean_before_sign as t
s = t.xml_assinado
for idx, line in enumerate(s.splitlines()):
    if idx < 10 or idx > len(s.splitlines()) - 10:
        print(f"L{idx+1}: {line[:80]}")
