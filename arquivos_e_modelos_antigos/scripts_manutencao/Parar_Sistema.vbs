Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FileExists(strScriptDir & "\Parar_Sistema.bat") Then
    strBat = strScriptDir & "\Parar_Sistema.bat"
ElseIf fso.FileExists(strScriptDir & "\gerador\Parar_Sistema.bat") Then
    strBat = strScriptDir & "\gerador\Parar_Sistema.bat"
Else
    strBat = "Parar_Sistema.bat"
End If

WshShell.Run Chr(34) & strBat & Chr(34), 0, True
