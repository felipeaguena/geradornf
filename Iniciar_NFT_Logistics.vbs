Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FolderExists(strScriptDir & "\gerador") Then
    strGeradorDir = strScriptDir & "\gerador"
Else
    strGeradorDir = strScriptDir
End If

strBat = strGeradorDir & "\.run_server.bat"

' 1. Executa o backend Flask em segundo plano ocultando 100% o console (parametro 0)
WshShell.Run "cmd.exe /c " & Chr(34) & strBat & Chr(34), 0, False

' 2. Aguarda o servidor responder no /api/ping antes de abrir o navegador
On Error Resume Next
Set oHttp = CreateObject("MSXML2.ServerXMLHTTP.6.0")
If Err.Number <> 0 Then
    Err.Clear
    Set oHttp = CreateObject("MSXML2.ServerXMLHTTP")
End If
On Error GoTo 0

If Not oHttp Is Nothing Then
    oHttp.setTimeouts 500, 500, 500, 500
    For i = 1 To 40 ' Tenta a cada 300ms por ate 12 segundos
        On Error Resume Next
        oHttp.Open "GET", "http://localhost:1652/api/ping", False
        oHttp.Send
        If Err.Number = 0 Then
            If oHttp.Status = 200 Then
                On Error GoTo 0
                Exit For
            End If
        End If
        On Error GoTo 0
        WScript.Sleep 300
    Next
Else
    WScript.Sleep 2000
End If

' 3. Localiza Chrome ou Edge para abrir em modo App (Janela de aplicativo independente que permite fechar via window.close)
strUrl = "http://localhost:1652"
strBrowserCmd = ""

If fso.FileExists("C:\Program Files\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """C:\Program Files\Google\Chrome\Application\chrome.exe"" --app=" & strUrl
ElseIf fso.FileExists("C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"" --app=" & strUrl
ElseIf fso.FileExists("C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"" --app=" & strUrl
ElseIf fso.FileExists("C:\Program Files\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """C:\Program Files\Microsoft\Edge\Application\msedge.exe"" --app=" & strUrl
Else
    strBrowserCmd = strUrl
End If

WshShell.Run strBrowserCmd
