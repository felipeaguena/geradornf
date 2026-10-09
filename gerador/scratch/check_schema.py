with open(r'gerador\venv\Lib\site-packages\nfelib\nfe\schemas\v4_0\leiauteNFe_v4.00.xsd', 'r', encoding='utf-8') as f:
    text = f.read()

pos = 0
while True:
    idx = text.find('Signature', pos)
    if idx == -1:
        break
    print(text[max(0, idx - 100): min(len(text), idx + 200)])
    print("="*40)
    pos = idx + 9
