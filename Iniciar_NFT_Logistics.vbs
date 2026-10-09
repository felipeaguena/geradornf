Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FolderExists(strScriptDir & "\gerador") Then
    strGeradorDir = strScriptDir & "\gerador"
Else
    strGeradorDir = strScriptDir
End If

strBat = strGeradorDir & "\.run_server.bat"
strLoadingFile = strScriptDir & "\loading.html"
WshShell.CurrentDirectory = strGeradorDir

Function CheckServer()
    Dim http
    CheckServer = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    If Err.Number <> 0 Then
        Err.Clear
        Set http = CreateObject("MSXML2.ServerXMLHTTP")
    End If
    If Not http Is Nothing Then
        http.setTimeouts 300, 300, 300, 300
        http.Open "GET", "http://127.0.0.1:1652/api/ping", False
        http.Send
        If Err.Number = 0 Then
            If http.Status = 200 Then
                CheckServer = True
            End If
        End If
    End If
    On Error GoTo 0
End Function

' 1. Verifica se o backend já está respondendo
bServerRunning = CheckServer()

' Se o servidor JÁ estiver rodando, abre direto o portal.
' Se NÃO estiver rodando, abre IMEDIATAMENTE a tela de loading em primeiro plano
' e inicia o servidor Python em segundo plano.
If bServerRunning Then
    strInitialUrl = "http://127.0.0.1:1652"
Else
    strInitialUrl = "file:///" & Replace(strLoadingFile, "\", "/")
    ' Inicia o servidor Python Flask em segundo plano
    WshShell.Run "cmd.exe /c " & Chr(34) & strBat & Chr(34), 0, False
End If

' 2. Localiza Chrome ou Edge para abrir em modo App (janela de aplicativo nativo)
strBrowserCmd = ""
strLocalAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
strProgramFiles = WshShell.ExpandEnvironmentStrings("%ProgramFiles%")
strProgramFilesX86 = WshShell.ExpandEnvironmentStrings("%ProgramFiles(x86)%")

If fso.FileExists(strProgramFiles & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strProgramFiles & "\Google\Chrome\Application\chrome.exe"" --app=""" & strInitialUrl & """"
ElseIf fso.FileExists(strProgramFilesX86 & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strProgramFilesX86 & "\Google\Chrome\Application\chrome.exe"" --app=""" & strInitialUrl & """"
ElseIf fso.FileExists(strLocalAppData & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strLocalAppData & "\Google\Chrome\Application\chrome.exe"" --app=""" & strInitialUrl & """"
ElseIf fso.FileExists(strProgramFiles & "\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """" & strProgramFiles & "\Microsoft\Edge\Application\msedge.exe"" --app=""" & strInitialUrl & """"
ElseIf fso.FileExists(strProgramFilesX86 & "\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """" & strProgramFilesX86 & "\Microsoft\Edge\Application\msedge.exe"" --app=""" & strInitialUrl & """"
Else
    strBrowserCmd = """" & strInitialUrl & """"
End If

' 3. Abre a janela instantaneamente na tela do usuário
WshShell.Run strBrowserCmd
