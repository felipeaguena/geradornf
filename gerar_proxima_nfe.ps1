param (
    [Parameter(Position=0)]
    [string]$Origem = "nfe_importacao_sebrae_web.xml",
    
    [Parameter(Position=1)]
    [int]$NumeroNF = 2,
    
    [Parameter(Position=2)]
    [string]$Destino = "",
    
    [int]$Serie = 1
)

if (-not (Test-Path $Origem)) {
    Write-Host "ERRO: Arquivo de origem '$Origem' nao encontrado." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Destino)) {
    $Destino = "nfe_numero_$NumeroNF.xml"
}

function Get-Modulo11($chave43) {
    $pesos = 2,3,4,5,6,7,8,9
    $soma = 0
    $idx = 0
    for ($i = $chave43.Length - 1; $i -ge 0; $i--) {
        $digito = [int]::Parse($chave43[$i])
        $soma += $digito * $pesos[$idx % $pesos.Length]
        $idx++
    }
    $resto = $soma % 11
    if ($resto -eq 0 -or $resto -eq 1) { return 0 }
    else { return 11 - $resto }
}

[xml]$xml = Get-Content -Path $Origem -Encoding UTF8
$ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace("nfe", "http://www.portalfiscal.inf.br/nfe")

$infNFe = $xml.SelectSingleNode("//nfe:infNFe", $ns)
$ide = $xml.SelectSingleNode("//nfe:ide", $ns)
$emit = $xml.SelectSingleNode("//nfe:emit", $ns)

if ($null -eq $infNFe -or $null -eq $ide -or $null -eq $emit) {
    Write-Host "ERRO: XML nao possui as tags <infNFe>, <ide> ou <emit> necessarias." -ForegroundColor Red
    exit 1
}

$cUF = $ide.SelectSingleNode("nfe:cUF", $ns).InnerText.PadLeft(2, '0')
$dhEmi = $ide.SelectSingleNode("nfe:dhEmi", $ns).InnerText
$aamm = $dhEmi.Substring(2,2) + $dhEmi.Substring(5,2)

$cnpjNode = $emit.SelectSingleNode("nfe:CNPJ", $ns)
$cpfNode = $emit.SelectSingleNode("nfe:CPF", $ns)
$docEmit = if ($cnpjNode) { $cnpjNode.InnerText.PadLeft(14, '0') } else { $cpfNode.InnerText.PadLeft(14, '0') }

$mod = $ide.SelectSingleNode("nfe:mod", $ns).InnerText.PadLeft(2, '0')

$ide.SelectSingleNode("nfe:serie", $ns).InnerText = $Serie.ToString()
$ide.SelectSingleNode("nfe:nNF", $ns).InnerText = $NumeroNF.ToString()

$serieFmt = $Serie.ToString().PadLeft(3, '0')
$nnfFmt = $NumeroNF.ToString().PadLeft(9, '0')

$novoCNF = (Get-Random -Minimum 10000000 -Maximum 99999999).ToString()
$ide.SelectSingleNode("nfe:cNF", $ns).InnerText = $novoCNF

$tpEmis = $ide.SelectSingleNode("nfe:tpEmis", $ns).InnerText

$chave43 = "$cUF$aamm$docEmit$mod$serieFmt$nnfFmt$tpEmis$novoCNF"
$cDV = Get-Modulo11 $chave43
$ide.SelectSingleNode("nfe:cDV", $ns).InnerText = $cDV.ToString()

$infNFe.SetAttribute("Id", "NFe$chave43$cDV")

$destinoPath = Join-Path (Get-Location) $Destino
$xml.Save($destinoPath)

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " SUCESSO: NF-e Numero $NumeroNF gerada com sucesso!" -ForegroundColor Green
Write-Host " Arquivo de Origem: $Origem" -ForegroundColor Yellow
Write-Host " Arquivo de Saida : $Destino" -ForegroundColor Yellow
Write-Host " Nova Chave SEFAZ : NFe$chave43$cDV" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
