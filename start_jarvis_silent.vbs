Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = currentDir & "\start_jarvis.ps1"
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & psScript & """ -Background", 0, False
Set WshShell = Nothing
Set fso = Nothing
