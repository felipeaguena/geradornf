import sefaz_client
try:
    xml = '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe35261047998441000198550010000000011000000013" versao="4.00"></infNFe></NFe>'
    signed = sefaz_client.assinar_xml(xml)
    print('SIGNED OK')
except Exception as e:
    import traceback
    traceback.print_exc()
