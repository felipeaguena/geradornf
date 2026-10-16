import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Create workbook
wb = openpyxl.Workbook()

# Style definitions
font_title = Font(name="Calibri", size=14, bold=True, color="1F497D")
font_subtitle = Font(name="Calibri", size=10, italic=True, color="595959")
font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
font_bold = Font(name="Calibri", size=10, bold=True)
font_regular = Font(name="Calibri", size=10)
font_alert = Font(name="Calibri", size=10, bold=True, color="C00000")

fill_header_navy = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
fill_header_green = PatternFill(start_color="1E7145", end_color="1E7145", fill_type="solid")
fill_header_orange = PatternFill(start_color="C55A11", end_color="C55A11", fill_type="solid")
fill_header_gray = PatternFill(start_color="595959", end_color="595959", fill_type="solid")

fill_zebra_light = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
fill_yellow_alert = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

thin_border_side = Side(border_style="thin", color="D9D9D9")
thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

align_center = Alignment(horizontal="center", vertical="center")
align_left = Alignment(horizontal="left", vertical="center")
align_right = Alignment(horizontal="right", vertical="center")

# ==========================================
# ABA 1: FEIRAS CONFIRMADAS 2027
# ==========================================
ws1 = wb.active
ws1.title = "Feiras Confirmadas 2027"
ws1.views.sheetView[0].showGridLines = True

# Title
ws1.merge_cells("A1:F1")
ws1["A1"] = "CALENDÁRIO OFICIAL DE FEIRAS E EVENTOS — 2027"
ws1["A1"].font = font_title
ws1["A1"].alignment = align_left

ws1.merge_cells("A2:F2")
ws1["A2"] = "Prazos recomendados com 30 dias de antecedência para entrega da carga/documentos no estande."
ws1["A2"].font = font_subtitle
ws1["A2"].alignment = align_left

headers1 = [
    "Item Original", "Nome da Feira", "Período Feira 2027", 
    "Prazo Limite (-30 dias)", "Pavilhão / Local", "Promotora / Organizadora"
]

ws1.append([]) # row 3 blank
ws1.append(headers1) # row 4 headers

for col_num, _ in enumerate(headers1, 1):
    cell = ws1.cell(row=4, column=col_num)
    cell.font = font_header
    cell.fill = fill_header_navy
    cell.alignment = align_center

data_confirmadas = [
    ("15", "CIOSP (44º)", "27 a 30 de janeiro de 2027", "28/12/2026", "Expo Center Norte (SP)", "APCD"),
    ("26", "EXPO REVESTIR", "22 a 26 de fevereiro de 2027", "23/01/2027", "São Paulo Expo", "NürnbergMesse"),
    ("38", "FESPA DIGITAL PRINTING", "01 a 04 de março de 2027", "30/01/2027", "Expo Center Norte (SP)", "APS Feiras"),
    ("64", "PLÁSTICO BRASIL (Bienal)", "15 a 19 de março de 2027", "13/02/2027", "São Paulo Expo", "Informa Markets"),
    ("05", "AUTOCOM", "30 de março a 01 de abril de 2027", "28/02/2027", "Expo Center Norte (SP)", "Francal Feiras"),
    ("34", "FEICON", "06 a 09 de abril de 2027", "07/03/2027", "São Paulo Expo", "RX Global"),
    ("65", "FIT PUERI EXPO", "06 a 08 de abril de 2027", "07/03/2027", "Distrito Anhembi (Novo Local)", "Koelnmesse"),
    ("06", "AUTOMEC (Bienal)", "20 a 24 de abril de 2027", "21/03/2027", "São Paulo Expo", "RX Global"),
    ("02", "AGRISHOW", "26 a 30 de abril de 2027", "27/03/2027", "Polo Regional (Ribeirão Preto - SP)", "Informa Markets"),
    ("57", "JPR (Jornada Paulista de Radiologia)", "29 de abril a 02 de maio de 2027", "30/03/2027", "Transamerica Expo Center (SP)", "SPR"),
    ("28", "EXPOMAFE (Bienal)", "04 a 08 de maio de 2027", "04/04/2027", "São Paulo Expo", "Informa Markets"),
    ("08", "BETT BRASIL", "04 a 07 de maio de 2027", "04/04/2027", "Expo Center Norte (SP)", "Hyve Group"),
    ("51", "HOSPITALAR", "18 a 21 de maio de 2027", "18/04/2027", "São Paulo Expo", "Informa Markets"),
    ("23", "EXPO ELEVADOR (Bienal)", "01 a 03 de junho de 2027", "02/05/2027", "Pro Magno (SP)", "Cardoso Almeida Eventos"),
    ("31", "FCE PHARMA / COSMETIQUE", "08 a 10 de junho de 2027", "09/05/2027", "São Paulo Expo", "NürnbergMesse"),
    ("30", "EXPOSEC", "08 a 10 de junho de 2027", "09/05/2027", "São Paulo Expo", "Fiera Milano"),
    ("18/19", "ELETROLAR & ELETROCAR SHOW", "21 a 24 de junho de 2027", "22/05/2027", "Distrito Anhembi (SP)", "Grupo Eletrolar"),
    ("44", "FISPAL TECNOLOGIA", "22 a 25 de junho de 2027", "23/05/2027", "São Paulo Expo", "Informa Markets"),
    ("52", "IFAT BRASIL", "23 a 25 de junho de 2027", "24/05/2027", "Expo Center Norte (Novo Local)", "Messe München"),
    ("46", "FUTURE PRINT", "13 a 16 de julho de 2027", "13/06/2027", "Distrito Anhembi (SP)", "Informa Markets"),
    ("41", "FIPAN", "20 a 23 de julho de 2027", "20/06/2027", "Expo Center Norte (SP)", "Seven - Sindipan"),
    ("21", "ESCOLAR OFFICE BRASIL", "01 a 04 de agosto de 2027", "02/07/2027", "Expo Center Norte (SP)", "Francal Feiras"),
    ("50", "HOME SHOW BRAZIL", "03 a 05 de agosto de 2027", "04/07/2027", "Distrito Anhembi (SP)", "Propórtio Promoções"),
    ("83", "PET SOUTH AMERICA", "11 a 13 de agosto de 2027", "12/07/2027", "Distrito Anhembi (SP)", "NürnbergMesse"),
    ("67", "SET EXPO", "16 a 19 de agosto de 2027", "17/07/2027", "Distrito Anhembi (SP)", "SET Comunicação"),
    ("16", "CONCRETE SHOW", "17 a 19 de agosto de 2027", "18/07/2027", "São Paulo Expo", "Informa Markets"),
    ("55/68", "INTERSOLAR / THE SMARTER E", "24 a 26 de agosto de 2027", "25/07/2027", "Expo Center Norte (SP)", "Solar Promotion"),
    ("07", "BEAUTY FAIR", "04 a 07 de setembro de 2027", "05/08/2027", "Expo Center Norte (SP)", "Beauty Fair Eventos"),
    ("33", "FEBRAVA (Bienal)", "14 a 17 de setembro de 2027", "15/08/2027", "São Paulo Expo", "RX Global"),
    ("40", "FIEE (Bienal)", "14 a 17 de setembro de 2027", "15/08/2027", "São Paulo Expo", "RX Global"),
    ("20", "EQUIPOTEL", "14 a 17 de setembro de 2027", "15/08/2027", "Expo Center Norte (SP)", "RX Global"),
    ("13", "CHINA HOMELIFE BRAZIL", "21 a 23 de setembro de 2027", "22/08/2027", "São Paulo Expo", "China Homelife"),
    ("53", "IN-COSMETICS LATIN AMERICA", "22 a 23 de setembro de 2027", "23/08/2027", "Expo Center Norte (SP)", "RX Global"),
    ("04", "ANALÍTICA LATIN AMERICA (Bienal)", "28 a 30 de setembro de 2027", "29/08/2027", "São Paulo Expo", "NürnbergMesse"),
    ("56", "INTRA-LOG EXPO", "28 a 30 de setembro de 2027", "29/08/2027", "Expo Center Norte (SP)", "Interlink Exhibitions"),
    ("81", "PAVING EXPO", "28 a 30 de setembro de 2027", "29/08/2027", "Distrito Anhembi (SP)", "STO Feiras"),
    ("66", "RIOPARTS (Bienal)", "29 de setembro a 02 de outubro de 2027", "30/08/2027", "Expo MAG (Rio de Janeiro - RJ)", "Diretriz Feiras"),
    ("47", "FUTURECOM", "05 a 07 de outubro de 2027", "05/09/2027", "São Paulo Expo", "Informa Markets"),
    ("85", "DATA CENTER WORLD BRASIL", "05 a 07 de outubro de 2027", "05/09/2027", "São Paulo Expo", "Informa Markets"),
    ("62", "NT EXPO (Bienal)", "19 a 21 de outubro de 2027", "19/09/2027", "Distrito Anhembi (SP)", "Informa Markets"),
    ("12", "BRAZIL WINDPOWER", "19 a 21 de outubro de 2027", "19/09/2027", "São Paulo Expo", "Informa Markets"),
    ("37", "FENASAN", "26 a 28 de outubro de 2027", "26/09/2027", "Expo Center Norte (SP)", "AESabesp"),
    ("69/72", "TUBOTECH & WIRE BRASIL (Bienal)", "27 a 29 de outubro de 2027", "27/09/2027", "São Paulo Expo", "Fiera Milano"),
    ("58", "M&T EXPO (Trienal: 2024-2027)", "16 a 19 de novembro de 2027", "17/10/2027", "São Paulo Expo", "Messe München")
]

for row_idx, row_data in enumerate(data_confirmadas, 5):
    for col_idx, val in enumerate(row_data, 1):
        cell = ws1.cell(row=row_idx, column=col_idx, value=val)
        cell.font = font_regular
        cell.border = thin_border
        if col_idx in [1, 4]:
            cell.alignment = align_center
        else:
            cell.alignment = align_left
        
        # Zebra striping
        if row_idx % 2 == 0:
            cell.fill = fill_zebra_light

        # Highlighting new locations
        if "Novo Local" in str(val):
            cell.fill = fill_yellow_alert
            cell.font = font_bold

# ==========================================
# ABA 2: FEIRAS BIENAIS (NÃO OCORREM 2027)
# ==========================================
ws2 = wb.create_sheet(title="Bienais - Próxima em 2028")
ws2.views.sheetView[0].showGridLines = True

ws2.merge_cells("A1:E1")
ws2["A1"] = "FEIRAS BIENAIS DE ANOS PARES (NÃO OCORREM EM 2027)"
ws2["A1"].font = font_title
ws2["A1"].alignment = align_left

ws2.merge_cells("A2:E2")
ws2["A2"] = "Eventos de ciclo par que ocorreram em 2026. Manter anotado como 2028 na planilha raiz para evitar equívocos."
ws2["A2"].font = font_subtitle
ws2["A2"].alignment = align_left

headers2 = [
    "Item Original", "Nome da Feira", "Última Edição (2026)", 
    "Próxima Edição Oficial (2028)", "Pavilhão / Local"
]

ws2.append([]) # row 3 blank
ws2.append(headers2)

for col_num, _ in enumerate(headers2, 1):
    cell = ws2.cell(row=4, column=col_num)
    cell.font = font_header
    cell.fill = fill_header_orange
    cell.alignment = align_center

data_bienais = [
    ("32 / 75", "FEBRATEX", "18 a 21 de agosto de 2026", "22 a 25 de agosto de 2028 (Em 2027 apenas Summit/palestras)", "Parque Vila Germânica (Blumenau/SC)"),
    ("35", "FEIMEC", "05 a 09 de maio de 2026", "09 a 13 de maio de 2028 (Alterna com Expomafe)", "São Paulo Expo"),
    ("42", "FISP", "06 a 08 de outubro de 2026", "03 a 05 de outubro de 2028", "São Paulo Expo"),
    ("45", "FORMÓBILE", "30/06 a 03/07/2026", "04 a 07 de julho de 2028", "São Paulo Expo"),
    ("61 / 87", "FENATRAN & MOVIMAT", "09 a 13 de novembro de 2026", "06 a 10 de novembro de 2028", "São Paulo Expo"),
    ("24", "EXPO LAZER", "11 a 14 de agosto de 2026", "08 a 11 de agosto de 2028", "Distrito Anhembi (SP)"),
    ("27", "EXPOLUX", "15 a 18 de setembro de 2026", "19 a 22 de setembro de 2028 (Alterna com FIEE)", "Expo Center Norte (SP)"),
    ("29", "EXPOPOSTOS", "08 a 10 de setembro de 2026", "Setembro de 2028", "São Paulo Expo"),
    ("76", "SIAVS", "04 a 06 de agosto de 2026", "01 a 03 de agosto de 2028", "Distrito Anhembi (SP)"),
    ("82", "FESQUA", "09 a 12 de setembro de 2026", "12 a 15 de setembro de 2028", "São Paulo Expo"),
    ("77", "LAT.BUS", "11 a 13 de agosto de 2026", "15 a 17 de agosto de 2028", "São Paulo Expo"),
    ("78", "MOVELSUL", "17 a 20 de agosto de 2026", "07 a 10 de agosto de 2028", "Parque de Eventos de Bento Gonçalves (RS)"),
    ("80", "PNEU SHOW", "23 a 25 de junho de 2026", "20 a 22 de junho de 2028", "Expo Center Norte (SP)"),
    ("54", "INTERPLAST", "25 a 28 de agosto de 2026", "Agosto de 2028", "Expoville (Joinville/SC)"),
    ("79", "ROG.E (Rio Oil & Gas)", "21 a 24 de setembro de 2026", "Setembro de 2028", "Riocentro (RJ)"),
    ("10", "BRASIL BRAU", "09 a 11 de junho de 2026", "Junho de 2028", "São Paulo Expo"),
    ("25", "EXPOPRINT LATIN AMERICA", "24 a 28 de março de 2026", "Evento Quadrienal — Próxima em 2030", "Expo Center Norte (SP)")
]

for row_idx, row_data in enumerate(data_bienais, 5):
    for col_idx, val in enumerate(row_data, 1):
        cell = ws2.cell(row=row_idx, column=col_idx, value=val)
        cell.font = font_regular
        cell.border = thin_border
        if col_idx in [1, 3]:
            cell.alignment = align_center
        else:
            cell.alignment = align_left
        if row_idx % 2 == 0:
            cell.fill = fill_zebra_light

# ==========================================
# ABA 3: HIGIENIZAÇÃO DA PLANILHA RAIZ
# ==========================================
ws3 = wb.create_sheet(title="Higienização de Linhas")
ws3.views.sheetView[0].showGridLines = True

ws3.merge_cells("A1:D1")
ws3["A1"] = "LINHAS RECOMENDADAS PARA HIGIENIZAÇÃO OU EXCLUSÃO"
ws3["A1"].font = font_title
ws3["A1"].alignment = align_left

ws3.merge_cells("A2:D2")
ws3["A2"] = "Itens da planilha que não são feiras comerciais regulares de estandes expositores."
ws3["A2"].font = font_subtitle
ws3["A2"].alignment = align_left

headers3 = ["Item Original", "Identificação na Planilha", "Motivo da Recomendação", "Ação Sugerida"]

ws3.append([])
ws3.append(headers3)

for col_num, _ in enumerate(headers3, 1):
    cell = ws3.cell(row=4, column=col_num)
    cell.font = font_header
    cell.fill = fill_header_gray
    cell.alignment = align_center

data_higienizacao = [
    ("14", "CINECOLOR (RADAR CINECOLOR)", "Sem dados de datas, local ou promotora comercial.", "Excluir da planilha"),
    ("17", "DVS", "Linha totalmente vazia.", "Excluir da planilha"),
    ("22", "EVENTO PRIVADO MAGNETTI MARELLI", "Encontro corporativo fechado de 1 único dia.", "Excluir da lista geral de feiras"),
    ("59", "MACKENZIE", "Evento acadêmico interno sem dados.", "Excluir da planilha"),
    ("70", "UFC RIO", "Evento esportivo de artes marciais (Farmasi Arena), não é feira B2B.", "Excluir ou transferir para eventos esportivos"),
    ("63", "OTC BRASIL", "Conferência pontual offshore do IBP, sem grade fixa anual.", "Manter sob demanda"),
    ("88", "WORLD CONFERENCE ON LUNG HEALTH", "Congresso médico mundial itinerante (ocorre em países diferentes a cada ano; no Brasil foi em 2026).", "Excluir (2027 será no exterior)")
]

for row_idx, row_data in enumerate(data_higienizacao, 5):
    for col_idx, val in enumerate(row_data, 1):
        cell = ws3.cell(row=row_idx, column=col_idx, value=val)
        cell.font = font_regular
        cell.border = thin_border
        if col_idx in [1]:
            cell.alignment = align_center
        else:
            cell.alignment = align_left
        if row_idx % 2 == 0:
            cell.fill = fill_zebra_light

# Auto-adjust column widths across all sheets
for ws in [ws1, ws2, ws3]:
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # ignore title merged cells in row 1 and 2
            if cell.row in [1, 2]:
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

# Save workbook
output_path = r"c:\Users\felipeaguena\Documents\XMLNFT\Relatorio_Feiras_2027.xlsx"
wb.save(output_path)
print("SUCCESS: File generated at", output_path)
