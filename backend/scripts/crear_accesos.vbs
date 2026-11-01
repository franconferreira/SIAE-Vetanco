Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = "F:\Escritorio\UADE\2026\Segundo_Cuatrimestre\Direccion de proyectos informaticos\TPO\siae-vetanco"
desktop = WshShell.SpecialFolders("Desktop")
vbsTarget = strDir & "\Iniciar SIAE.vbs"

' 1. Crear / actualizar acceso en carpeta del proyecto
Set lnk1 = WshShell.CreateShortcut(strDir & "\SIAE-Vetanco.lnk")
lnk1.TargetPath = "wscript.exe"
lnk1.Arguments = """" & vbsTarget & """"
lnk1.WorkingDirectory = strDir
lnk1.Description = "Sistema Integrado de Automatizacion y Enlace - Vetanco"
lnk1.Save

' 2. Crear / actualizar acceso en Escritorio
Set lnk2 = WshShell.CreateShortcut(desktop & "\SIAE Vetanco.lnk")
lnk2.TargetPath = "wscript.exe"
lnk2.Arguments = """" & vbsTarget & """"
lnk2.WorkingDirectory = strDir
lnk2.Description = "Sistema Integrado de Automatizacion y Enlace - Vetanco"
lnk2.Save

WScript.Echo "Shortcuts creados con exito."
