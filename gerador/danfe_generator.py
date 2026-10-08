import os
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pymupdf as fitz
import barcode
from barcode.writer import ImageWriter

class DanfeGenerator:
    def __init__(self, template_path=None):
        if template_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(base_dir, "modelo", "danfe_template_clean.pdf")
        self.template_path = template_path

    @staticmethod
    def format_currency(val):
        try:
            f = float(val) if val is not None else 0.0
            return f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"

    @staticmethod
    def format_qty(val, decimals=4):
        try:
            f = float(val) if val is not None else 0.0
            fmt = f"{{:,.{decimals}f}}"
            return fmt.format(f).replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,0000"

    @staticmethod
    def format_weight(val):
        try:
            f = float(val) if val is not None else 0.0
            return f"{f:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,000"

    @staticmethod
    def format_cnpj_cpf(val):
        val = re.sub(r"\D", "", str(val or ""))
        if len(val) == 14:
            return f"{val[:2]}.{val[2:5]}.{val[5:8]}/{val[8:12]}-{val[12:]}"
        elif len(val) == 11:
            return f"{val[:3]}.{val[3:6]}.{val[6:9]}-{val[9:]}"
        return val

    @staticmethod
    def format_cep(val):
        val = re.sub(r"\D", "", str(val or ""))
        if len(val) == 8:
            return f"{val[:5]}-{val[5:]}"
        return val

    @staticmethod
    def format_chave(chave):
        chave = re.sub(r"\D", "", str(chave or ""))
        return " ".join([chave[i:i+4] for i in range(0, len(chave), 4)])

    @staticmethod
    def format_doc_number(n_nf):
        try:
            n = int(re.sub(r"\D", "", str(n_nf or "0")))
            s = f"{n:09d}"
            return f"Nº. {s[:3]}.{s[3:6]}.{s[6:]}"
        except Exception:
            return f"Nº. {n_nf}"

    def parse_xml(self, xml_content_or_path):
        if os.path.exists(xml_content_or_path):
            tree = ET.parse(xml_content_or_path)
            root = tree.getroot()
        else:
            root = ET.fromstring(xml_content_or_path)

        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        if not root.tag.endswith("NFe") and not root.tag.endswith("nfeProc"):
            # Check without namespace
            pass

        # Helper xpath
        def find_txt(elem, path, default=""):
            if elem is None:
                return default
            node = elem.find(path, ns)
            if node is None:
                # try without prefix
                clean_path = re.sub(r"nfe:", "", path)
                node = elem.find(clean_path)
            return node.text.strip() if (node is not None and node.text) else default

        # Extrair chave e protocolo se for nfeProc ou se tiver infProt
        chave = ""
        prot_txt = ""
        inf_prot = root.find(".//nfe:infProt", ns) or root.find(".//infProt")
        if inf_prot is not None:
            chave = find_txt(inf_prot, "nfe:chNFe")
            n_prot = find_txt(inf_prot, "nfe:nProt")
            dh_rec = find_txt(inf_prot, "nfe:dhRecbto")
            if dh_rec:
                try:
                    dt = datetime.fromisoformat(dh_rec.replace("Z", "+00:00"))
                    dh_rec_str = dt.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    dh_rec_str = dh_rec
                prot_txt = f"{n_prot}  -  {dh_rec_str}"
            else:
                prot_txt = n_prot

        inf_nfe = root.find(".//nfe:infNFe", ns) or root.find(".//infNFe")
        if not chave and inf_nfe is not None:
            nfe_id = inf_nfe.attrib.get("Id", "")
            chave = re.sub(r"\D", "", nfe_id)

        ide = inf_nfe.find("nfe:ide", ns) or inf_nfe.find("ide") if inf_nfe is not None else None
        emit = inf_nfe.find("nfe:emit", ns) or inf_nfe.find("emit") if inf_nfe is not None else None
        dest = inf_nfe.find("nfe:dest", ns) or inf_nfe.find("dest") if inf_nfe is not None else None
        tot = inf_nfe.find(".//nfe:ICMSTot", ns) or inf_nfe.find(".//ICMSTot") if inf_nfe is not None else None
        transp = inf_nfe.find("nfe:transp", ns) or inf_nfe.find("transp") if inf_nfe is not None else None
        inf_adic = inf_nfe.find("nfe:infAdic", ns) or inf_nfe.find("infAdic") if inf_nfe is not None else None

        # IDE
        n_nf = find_txt(ide, "nfe:nNF", "0")
        serie = str(int(find_txt(ide, "nfe:serie", "1"))).zfill(3)
        tp_nf = find_txt(ide, "nfe:tpNF", "1")
        nat_op = find_txt(ide, "nfe:natOp", "")
        dh_emi = find_txt(ide, "nfe:dhEmi", "")
        dh_sai_ent = find_txt(ide, "nfe:dhSaiEnt", "")

        def parse_dt(dt_str):
            if not dt_str:
                return "", ""
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S")
            except Exception:
                parts = dt_str.split("T")
                d_p = parts[0].split("-")
                d_fmt = f"{d_p[2]}/{d_p[1]}/{d_p[0]}" if len(d_p) == 3 else dt_str
                h_fmt = parts[1][:8] if len(parts) > 1 else "00:00:00"
                return d_fmt, h_fmt

        dt_emi, _ = parse_dt(dh_emi)
        dt_sai, hr_sai = parse_dt(dh_sai_ent)

        # EMITENTE
        x_emit = find_txt(emit, "nfe:xNome", "NFT LOGISTICS LTDA")

        # DESTINATÁRIO
        x_dest = find_txt(dest, "nfe:xNome", "")
        cnpj_dest = find_txt(dest, "nfe:CNPJ") or find_txt(dest, "nfe:CPF") or find_txt(dest, "nfe:idEstrangeiro")
        ie_dest = find_txt(dest, "nfe:IE", "ISENTO")
        ender_dest = dest.find("nfe:enderDest", ns) if dest is not None else None
        x_lgr = find_txt(ender_dest, "nfe:xLgr")
        nro = find_txt(ender_dest, "nfe:nro")
        x_cpl = find_txt(ender_dest, "nfe:xCpl")
        dest_logr = f"{x_lgr}, {nro}" + (f" - {x_cpl}" if x_cpl else "")
        bairro_dest = find_txt(ender_dest, "nfe:xBairro")
        cep_dest = find_txt(ender_dest, "nfe:CEP")
        mun_dest = find_txt(ender_dest, "nfe:xMun")
        uf_dest = find_txt(ender_dest, "nfe:UF")
        fone_dest = find_txt(ender_dest, "nfe:fone")

        # TOTAIS
        v_bc = find_txt(tot, "nfe:vBC", "0.00")
        v_icms = find_txt(tot, "nfe:vICMS", "0.00")
        v_bc_st = find_txt(tot, "nfe:vBCST", "0.00")
        v_st = find_txt(tot, "nfe:vST", "0.00")
        v_ii = find_txt(tot, "nfe:vII", "0.00")
        v_pis = find_txt(tot, "nfe:vPIS", "0.00")
        v_prod = find_txt(tot, "nfe:vProd", "0.00")
        v_frete = find_txt(tot, "nfe:vFrete", "0.00")
        v_seg = find_txt(tot, "nfe:vSeg", "0.00")
        v_desc = find_txt(tot, "nfe:vDesc", "0.00")
        v_outro = find_txt(tot, "nfe:vOutro", "0.00")
        v_ipi = find_txt(tot, "nfe:vIPI", "0.00")
        v_cofins = find_txt(tot, "nfe:vCOFINS", "0.00")
        v_nf = find_txt(tot, "nfe:vNF", "0.00")

        # TRANSPORTE
        mod_frete = find_txt(transp, "nfe:modFrete", "1")
        frete_modalidade_map = {
            "0": "0-Emitente",
            "1": "1-Destinatário",
            "2": "2-Terceiros",
            "3": "3-Próprio Rem.",
            "4": "4-Próprio Dest.",
            "9": "9-Sem Frete"
        }
        frete_desc = frete_modalidade_map.get(str(mod_frete), "1-Destinatário")

        transp_aero = transp.find("nfe:transporta", ns) if transp is not None else None
        x_transp = find_txt(transp_aero, "nfe:xNome")
        cnpj_transp = find_txt(transp_aero, "nfe:CNPJ") or find_txt(transp_aero, "nfe:CPF")
        ie_transp = find_txt(transp_aero, "nfe:IE")
        end_transp = find_txt(transp_aero, "nfe:xEnder")
        mun_transp = find_txt(transp_aero, "nfe:xMun")
        uf_transp = find_txt(transp_aero, "nfe:UF")

        veic = transp.find("nfe:veicTransp", ns) if transp is not None else None
        placa = find_txt(veic, "nfe:placa")
        uf_veic = find_txt(veic, "nfe:UF")
        rntc = find_txt(veic, "nfe:RNTC")

        vol = transp.find("nfe:vol", ns) if transp is not None else None
        q_vol = find_txt(vol, "nfe:qVol")
        esp_vol = find_txt(vol, "nfe:esp")
        marca_vol = find_txt(vol, "nfe:marca")
        n_vol = find_txt(vol, "nfe:nVol")
        peso_l = find_txt(vol, "nfe:pesoL")
        peso_b = find_txt(vol, "nfe:pesoB")

        # PRODUTOS
        det_list = inf_nfe.findall("nfe:det", ns) if inf_nfe is not None else []
        itens = []
        for det in det_list:
            p = det.find("nfe:prod", ns)
            imposto = det.find("nfe:imposto", ns)
            c_prod = find_txt(p, "nfe:cProd")
            x_prod = find_txt(p, "nfe:xProd")
            ncm = find_txt(p, "nfe:NCM")
            cfop = find_txt(p, "nfe:CFOP")
            u_com = find_txt(p, "nfe:uCom")
            q_com = find_txt(p, "nfe:qCom")
            v_un_com = find_txt(p, "nfe:vUnCom")
            u_trib = find_txt(p, "nfe:uTrib")
            q_trib = find_txt(p, "nfe:qTrib")
            v_un_trib = find_txt(p, "nfe:vUnTrib")
            v_prod_item = find_txt(p, "nfe:vProd")

            # Orig / CSOSN / CST
            icms_det = imposto.find(".//nfe:ICMS", ns) if imposto is not None else None
            orig = "0"
            cst_csosn = ""
            v_bc_item = "0.00"
            v_icms_item = "0.00"
            p_icms_item = "0.00"
            if icms_det is not None and len(icms_det) > 0:
                child = icms_det[0]
                orig = find_txt(child, "nfe:orig", "0")
                cst_csosn = find_txt(child, "nfe:CSOSN") or find_txt(child, "nfe:CST")
                v_bc_item = find_txt(child, "nfe:vBC", "0.00")
                v_icms_item = find_txt(child, "nfe:vICMS", "0.00")
                p_icms_item = find_txt(child, "nfe:pICMS", "0.00")

            ipi_det = imposto.find(".//nfe:IPI", ns) if imposto is not None else None
            v_ipi_item = find_txt(ipi_det, ".//nfe:vIPI", "0.00")
            p_ipi_item = find_txt(ipi_det, ".//nfe:pIPI", "0.00")

            itens.append({
                "cProd": c_prod,
                "xProd": x_prod,
                "NCM": ncm,
                "orig_csosn": f"{orig}/{cst_csosn}" if cst_csosn else orig,
                "CFOP": cfop,
                "uCom": u_com,
                "qCom": q_com,
                "vUnCom": v_un_com,
                "uTrib": u_trib,
                "qTrib": q_trib,
                "vUnTrib": v_un_trib,
                "vProd": v_prod_item,
                "vBC": v_bc_item,
                "vICMS": v_icms_item,
                "vIPI": v_ipi_item,
                "pICMS": p_icms_item,
                "pIPI": p_ipi_item
            })

        # DADOS ADICIONAIS
        inf_cpl = find_txt(inf_adic, "nfe:infCpl")

        return {
            "chave": chave,
            "protocolo": prot_txt,
            "nNF": n_nf,
            "serie": serie,
            "tpNF": tp_nf,
            "natOp": nat_op,
            "dtEmi": dt_emi,
            "dtSai": dt_sai,
            "hrSai": hr_sai,
            "emitente": {"xNome": x_emit},
            "destinatario": {
                "xNome": x_dest,
                "cnpj_cpf": self.format_cnpj_cpf(cnpj_dest),
                "endereco": dest_logr,
                "bairro": bairro_dest,
                "cep": self.format_cep(cep_dest),
                "municipio": mun_dest,
                "uf": uf_dest,
                "fone": fone_dest,
                "ie": ie_dest
            },
            "totais": {
                "vBC": self.format_currency(v_bc),
                "vICMS": self.format_currency(v_icms),
                "vBCST": self.format_currency(v_bc_st),
                "vST": self.format_currency(v_st),
                "vII": self.format_currency(v_ii),
                "vPIS": self.format_currency(v_pis),
                "vProd": self.format_currency(v_prod),
                "vFrete": self.format_currency(v_frete),
                "vSeg": self.format_currency(v_seg),
                "vDesc": self.format_currency(v_desc),
                "vOutro": self.format_currency(v_outro),
                "vIPI": self.format_currency(v_ipi),
                "vCOFINS": self.format_currency(v_cofins),
                "vNF": self.format_currency(v_nf)
            },
            "transporte": {
                "frete": frete_desc,
                "xNome": x_transp,
                "cnpj_cpf": self.format_cnpj_cpf(cnpj_transp),
                "ie": ie_transp,
                "endereco": end_transp,
                "municipio": mun_transp,
                "uf": uf_transp,
                "placa": placa,
                "ufVeic": uf_veic,
                "antt": rntc,
                "qVol": q_vol,
                "esp": esp_vol,
                "marca": marca_vol,
                "num": n_vol,
                "pesoB": self.format_weight(peso_b) if peso_b else "",
                "pesoL": self.format_weight(peso_l) if peso_l else ""
            },
            "itens": itens,
            "infCpl": inf_cpl
        }

    def generate_barcode_image(self, chave):
        chave_clean = re.sub(r"\D", "", chave)
        if len(chave_clean) != 44:
            return None
        code128 = barcode.get("code128", chave_clean, writer=ImageWriter())
        fp = io.BytesIO()
        code128.write(fp, options={
            "write_text": False,
            "quiet_zone": 1.0,
            "module_height": 10.0,
            "font_size": 0
        })
        fp.seek(0)
        return fp.getvalue()

    def render(self, xml_path_or_content, output_pdf_path):
        data = self.parse_xml(xml_path_or_content)
        doc = fitz.open(self.template_path)
        page = doc[0]

        # Inserir Código de Barras
        if data["chave"]:
            img_bytes = self.generate_barcode_image(data["chave"])
            if img_bytes:
                # Retângulo do código de barras
                barcode_rect = fitz.Rect(355, 68, 582, 105)
                page.insert_image(barcode_rect, stream=img_bytes)

            # Chave formatada
            chave_fmt = self.format_chave(data["chave"])
            page.insert_text(fitz.Point(360.2, 129.0), chave_fmt, fontsize=8.0, fontname="Helvetica-Bold")

        # Canhoto do Rodapé / Topo
        n_nf_fmt = self.format_doc_number(data["nNF"])
        serie_fmt = f"Série {data['serie']}"
        page.insert_text(fitz.Point(498.3, 33.5), n_nf_fmt, fontsize=10.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(512.4, 43.5), serie_fmt, fontsize=10.0, fontname="Helvetica-Bold")

        canhoto_info = f"EMISSÃO: {data['dtEmi']}  VALOR TOTAL: R$ {data['totais']['vNF']}  DESTINATÁRIO: {data['destinatario']['xNome']} - {data['destinatario']['endereco']}"
        page.insert_text(fitz.Point(7.1, 23.5), canhoto_info[:120], fontsize=7.0, fontname="Helvetica")
        if data['destinatario']['bairro'] or data['destinatario']['municipio']:
            canhoto_loc = f"{data['destinatario']['bairro']} {data['destinatario']['municipio']}-{data['destinatario']['uf']}"
            page.insert_text(fitz.Point(7.1, 30.5), canhoto_loc, fontsize=7.0, fontname="Helvetica")

        # Cabeçalho DANFE
        page.insert_text(fitz.Point(324.1, 117.0), str(data["tpNF"]), fontsize=10.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(257.4, 134.5), n_nf_fmt, fontsize=10.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(271.4, 143.0), serie_fmt, fontsize=10.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(276.7, 151.5), "Folha 1/1", fontsize=8.0, fontname="Helvetica-Oblique")

        # Protocolo e Nat Op
        page.insert_text(fitz.Point(7.1, 172.0), data["natOp"][:45], fontsize=8.0, fontname="Helvetica-Bold")
        if data["protocolo"]:
            page.insert_text(fitz.Point(371.0, 172.0), data["protocolo"], fontsize=9.5, fontname="Helvetica-Bold")

        # Destinatário
        d = data["destinatario"]
        page.insert_text(fitz.Point(7.1, 223.0), d["xNome"][:45], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(364.2, 223.0), d["cnpj_cpf"], fontsize=9.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(517.8, 223.0), data["dtEmi"], fontsize=9.0, fontname="Helvetica-Bold")

        page.insert_text(fitz.Point(7.1, 243.0), d["endereco"][:45], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(282.0, 243.0), d["bairro"][:20], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(403.9, 243.0), d["cep"], fontsize=9.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(517.8, 243.0), data["dtSai"], fontsize=9.0, fontname="Helvetica-Bold")

        page.insert_text(fitz.Point(7.1, 263.0), d["municipio"][:35], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(285.3, 263.0), d["uf"], fontsize=9.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(304.7, 263.0), d["fone"][:15], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(401.1, 263.0), d["ie"], fontsize=9.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(522.8, 263.0), data["hrSai"], fontsize=9.0, fontname="Helvetica-Bold")

        # Totais e Impostos
        # Linha 1 (Y=294): vBC, vICMS, vBCST, vST, vII, vPIS, vProd
        t = data["totais"]
        def r_align(text, x_right, y, sz=8.0):
            # approximate width for Helvetica bold
            w = fitz.get_text_length(text, fontname="Helvetica-Bold", fontsize=sz)
            page.insert_text(fitz.Point(x_right - w, y), text, fontsize=sz, fontname="Helvetica-Bold")

        r_align(t["vBC"], 87.7, 294.0)
        r_align(t["vICMS"], 171.1, 294.0)
        r_align(t["vBCST"], 254.5, 294.0)
        r_align(t["vST"], 337.9, 294.0)
        r_align(t["vII"], 421.4, 294.0)
        r_align(t["vPIS"], 504.8, 294.0)
        r_align(t["vProd"], 588.2, 294.0)

        # Linha 2 (Y=314): vFrete, vSeg, vDesc, vOutro, vIPI, vCOFINS, vNF
        r_align(t["vFrete"], 87.7, 314.0)
        r_align(t["vSeg"], 171.1, 314.0)
        r_align(t["vDesc"], 254.5, 314.0)
        r_align(t["vOutro"], 337.9, 314.0)
        r_align(t["vIPI"], 421.4, 314.0)
        r_align(t["vCOFINS"], 504.8, 314.0)
        r_align(t["vNF"], 588.2, 314.0)

        # Transportador
        tr = data["transporte"]
        page.insert_text(fitz.Point(7.1, 345.0), tr["xNome"][:35], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(185.5, 345.0), tr["frete"], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(265.0, 345.0), tr["antt"], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(352.0, 345.0), tr["placa"], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(440.0, 345.0), tr["ufVeic"], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(462.0, 345.0), tr["cnpj_cpf"], fontsize=8.0, fontname="Helvetica-Bold")

        page.insert_text(fitz.Point(7.1, 365.0), tr["endereco"][:45], fontsize=7.5, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(265.0, 365.0), tr["municipio"][:25], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(440.0, 365.0), tr["uf"], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(492.0, 365.0), tr["ie"], fontsize=8.0, fontname="Helvetica-Bold")

        if tr["qVol"]:
            page.insert_text(fitz.Point(20.0, 385.0), str(tr["qVol"]), fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(66.2, 385.0), tr["esp"][:20], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(166.0, 385.0), tr["marca"][:15], fontsize=8.0, fontname="Helvetica-Bold")
        page.insert_text(fitz.Point(265.0, 385.0), tr["num"][:15], fontsize=8.0, fontname="Helvetica-Bold")
        if tr["pesoB"]:
            r_align(tr["pesoB"], 477.6, 385.0)
        if tr["pesoL"]:
            r_align(tr["pesoL"], 588.2, 385.0)

        # Itens da NF (Y inicial = 420.0)
        y_item = 420.0
        for it in data["itens"]:
            if y_item > 730:
                break # Se exceder a página 1 (no DANFE padrão cabe ~15 itens de 2 linhas)

            # Quebrar descrição em linhas de até 35 caracteres
            x_prod_lines = []
            words = it["xProd"].split(" ")
            cur_line = ""
            for w in words:
                if len(cur_line + " " + w) <= 35:
                    cur_line = (cur_line + " " + w).strip()
                else:
                    if cur_line:
                        x_prod_lines.append(cur_line)
                    cur_line = w
            if cur_line:
                x_prod_lines.append(cur_line)

            # Imprimir linha 1 das colunas
            page.insert_text(fitz.Point(15.8, y_item), it["cProd"][:10], fontsize=5.0, fontname="Helvetica")
            page.insert_text(fitz.Point(46.8, y_item), x_prod_lines[0] if x_prod_lines else "", fontsize=5.0, fontname="Helvetica")
            page.insert_text(fitz.Point(181.6, y_item), it["NCM"][:8], fontsize=5.0, fontname="Helvetica")
            page.insert_text(fitz.Point(208.0, y_item), it["orig_csosn"][:6], fontsize=5.0, fontname="Helvetica")
            page.insert_text(fitz.Point(226.9, y_item), it["CFOP"][:4], fontsize=5.0, fontname="Helvetica")
            page.insert_text(fitz.Point(246.0, y_item), it["uCom"][:3], fontsize=5.0, fontname="Helvetica")
            
            # Alinhamentos numéricos
            def r_align_item(txt, x_right, y):
                w = fitz.get_text_length(txt, fontname="Helvetica", fontsize=5.0)
                page.insert_text(fitz.Point(x_right - w, y), txt, fontsize=5.0, fontname="Helvetica")

            r_align_item(self.format_qty(it["qCom"]), 296.2, y_item)
            r_align_item(self.format_qty(it["vUnCom"]), 330.2, y_item)
            page.insert_text(fitz.Point(336.7, y_item), it["uTrib"][:3], fontsize=5.0, fontname="Helvetica")
            r_align_item(self.format_qty(it["qTrib"]), 386.9, y_item)
            r_align_item(self.format_qty(it["vUnTrib"]), 420.9, y_item)
            r_align_item(self.format_currency(it["vProd"]), 455.0, y_item)
            r_align_item(self.format_currency(it["vBC"]), 489.0, y_item)
            r_align_item(self.format_currency(it["vICMS"]), 523.0, y_item)
            r_align_item(self.format_currency(it["vIPI"]), 550.0, y_item)
            r_align_item(self.format_currency(it["pICMS"]), 571.2, y_item)

            # Imprimir linhas subsequentes da descrição
            for extra_line in x_prod_lines[1:]:
                y_item += 5.0
                page.insert_text(fitz.Point(46.8, y_item), extra_line, fontsize=5.0, fontname="Helvetica")

            y_item += 9.0

        # Dados Adicionais / Inf Cpl (Y=762.0 a 820.0)
        if data["infCpl"]:
            # Quebrar texto em linhas de ~95 caracteres
            txt_cpl = data["infCpl"].replace("\r\n", " ").replace("\n", " ")
            cpl_words = txt_cpl.split(" ")
            cpl_lines = []
            c_line = "Inf. Contribuinte: "
            for w in cpl_words:
                if len(c_line + " " + w) <= 90:
                    c_line = (c_line + " " + w).strip()
                else:
                    cpl_lines.append(c_line)
                    c_line = w
            if c_line:
                cpl_lines.append(c_line)

            y_cpl = 762.0
            for l_txt in cpl_lines[:8]: # até 8 linhas
                page.insert_text(fitz.Point(7.1, y_cpl), l_txt, fontsize=7.5, fontname="Helvetica")
                y_cpl += 8.0

        # Rodapé com data/hora de impressão
        now_str = datetime.now().strftime("%d/%m/%Y as %H:%M:%S")
        footer_txt = f"Impresso em {now_str}  GETT Tecnologia - gett.com.br"
        page.insert_text(fitz.Point(7.1, 836.0), footer_txt, fontsize=6.0, fontname="Helvetica-Oblique")

        doc.save(output_pdf_path)
        doc.close()
        print(f"DANFE PDF gerado com sucesso em: {output_pdf_path}")
