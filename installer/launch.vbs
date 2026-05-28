Option Explicit

Dim WShell, FSO, script_dir, python_exe, app_py
Dim oExec, strResult

Set WShell = CreateObject("WScript.Shell")
Set FSO    = CreateObject("Scripting.FileSystemObject")

script_dir = FSO.GetParentFolderName(WScript.ScriptFullName) & "\"
python_exe = script_dir & ".venv\Scripts\python.exe"
app_py     = script_dir & "app.py"

' ── Sanity check ────────────────────────────────────────────────────────────
If Not FSO.FileExists(python_exe) Then
    MsgBox "Trade Log is not set up yet." & vbCrLf & vbCrLf & _
           "Please run  'INSTALL - Double-Click This First.bat'  first.", _
           vbExclamation, "Trade Log"
    WScript.Quit
End If

' ── Check if already running on port 8502 ───────────────────────────────────
Set oExec = WShell.Exec("netstat -an")
strResult = oExec.StdOut.ReadAll

If InStr(strResult, ":8502") > 0 Then
    ' Already running — just open the browser
    WShell.Run "http://localhost:8502"
    WScript.Quit
End If

' ── Start Streamlit on port 8502 (hidden window) ────────────────────────────
WShell.Run "cmd /c """ & python_exe & """ -m streamlit run """ & _
           app_py & """ --server.port 8502" & _
           " --server.headless true > nul 2>&1", 0, False

WScript.Sleep 4000

' ── Open browser ─────────────────────────────────────────────────────────────
WShell.Run "http://localhost:8502"
