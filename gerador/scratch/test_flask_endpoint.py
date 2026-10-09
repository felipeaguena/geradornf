import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app, DOWNLOADS_DIR

client = app.test_client()

xml_path = r'C:\Users\felipeaguena\Documents\XMLNFT\last_290.xml'
with open(xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

print("Enviando requisição POST para /api/sefaz/enviar...")
response = client.post('/api/sefaz/enviar', json={
    'xml': xml_content,
    'chave': 'N/A',
    'tpAmb': 2
})

print(f"Status Code HTTP: {response.status_code}")
data = response.get_json()
print("Retorno JSON:")
for k, v in data.items():
    if k != 'response_xml':
        print(f"  {k}: {v}")

chave = data.get('chave')
if chave and chave != 'N/A':
    pdf_path = os.path.join(DOWNLOADS_DIR, f"{chave}-danfe.pdf")
    xml_out_path = os.path.join(DOWNLOADS_DIR, f"{chave}-nfe.xml")
    zip_path = os.path.join(DOWNLOADS_DIR, f"{chave}-arquivos.zip")
    print("\nVerificação dos arquivos gerados em downloads:")
    print(f"  PDF existe? {os.path.exists(pdf_path)} (tamanho: {os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0} bytes)")
    print(f"  XML existe? {os.path.exists(xml_out_path)} (tamanho: {os.path.getsize(xml_out_path) if os.path.exists(xml_out_path) else 0} bytes)")
    print(f"  ZIP existe? {os.path.exists(zip_path)} (tamanho: {os.path.getsize(zip_path) if os.path.exists(zip_path) else 0} bytes)")

if data.get('cstat') == '100' and data.get('autorizado') is True:
    print("\n>>> SUCESSO TOTAL! SEFAZ Homologação retornou Código 100 e Autorizou a NF-e! <<<")
else:
    print("\n>>> Falha ou rejeição <<<")
