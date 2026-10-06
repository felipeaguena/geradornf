Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FolderExists(strScriptDir & "\gerador") Then
    strGeradorDir = strScriptDir & "\gerador"
Else
    strGeradorDir = strScriptDir
End If

strBat = strGeradorDir & "\.run_server.bat"
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
        http.setTimeouts 400, 400, 400, 400
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

' Se ainda não estiver rodando, inicia o backend Flask em segundo plano
If Not bServerRunning Then
    WshShell.Run "cmd.exe /c " & Chr(34) & strBat & Chr(34), 0, False

    ' 2. Aguarda o servidor responder no /api/ping antes de abrir o navegador
    For i = 1 To 50 ' Tenta por até 15 segundos (50 x 300ms)
        If CheckServer() Then
            bServerRunning = True
            Exit For
        End If
        WScript.Sleep 300
    Next
End If

If Not bServerRunning Then
    MsgBox "O servidor do sistema (porta 1652) não respondeu a tempo." & vbCrLf & vbCrLf & _
           "Dica de diagnóstico:" & vbCrLf & _
           "Execute o arquivo 'gerador\.run_server.bat' para ver se há alguma mensagem de erro do Python no terminal.", _
           vbExclamation, "NFT Logistics - Aviso"
    WScript.Quit
End If

' 3. Localiza Chrome ou Edge para abrir em modo App (janela de aplicativo independente)
strUrl = "http://127.0.0.1:1652"
strBrowserCmd = ""

strLocalAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
strProgramFiles = WshShell.ExpandEnvironmentStrings("%ProgramFiles%")
strProgramFilesX86 = WshShell.ExpandEnvironmentStrings("%ProgramFiles(x86)%")

If fso.FileExists(strProgramFiles & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strProgramFiles & "\Google\Chrome\Application\chrome.exe"" --app=" & strUrl
ElseIf fso.FileExists(strProgramFilesX86 & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strProgramFilesX86 & "\Google\Chrome\Application\chrome.exe"" --app=" & strUrl
ElseIf fso.FileExists(strLocalAppData & "\Google\Chrome\Application\chrome.exe") Then
    strBrowserCmd = """" & strLocalAppData & "\Google\Chrome\Application\chrome.exe"" --app=" & strUrl
ElseIf fso.FileExists(strProgramFiles & "\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """" & strProgramFiles & "\Microsoft\Edge\Application\msedge.exe"" --app=" & strUrl
ElseIf fso.FileExists(strProgramFilesX86 & "\Microsoft\Edge\Application\msedge.exe") Then
    strBrowserCmd = """" & strProgramFilesX86 & "\Microsoft\Edge\Application\msedge.exe"" --app=" & strUrl
Else
    strBrowserCmd = strUrl
End If

WshShell.Run strBrowserCmd
