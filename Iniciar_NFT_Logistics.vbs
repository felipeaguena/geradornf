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

' 2. Aguarda o servidor inicializar
WScript.Sleep 2000

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
