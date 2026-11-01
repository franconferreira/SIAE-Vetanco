' Lanzador Silencioso 1-Click para SIAE-Vetanco
' Ejecuta el sistema en segundo plano sin ventanas de consola visibles.
' Al cerrar la pagina web, el sistema se cierra automaticamente.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = strDir
pythonw = strDir & "\backend\venv\Scripts\pythonw.exe"
runner = strDir & "\launcher.py"

' Comprobar que existe el ejecutable pythonw
If Not fso.FileExists(pythonw) Then
    MsgBox "No se encontro el entorno virtual en 'backend\venv'." & vbCrLf & "Ejecute 'iniciar_siae.bat' una primera vez para configurar dependencias.", vbCritical, "SIAE-Vetanco"
    WScript.Quit 1
End If

' 0 = Ventana oculta (SW_HIDE), False = No bloquear
WshShell.Run """" & pythonw & """ """ & runner & """", 0, False
