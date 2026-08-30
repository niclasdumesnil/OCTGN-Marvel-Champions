@echo off
for /r "%~dp0" %%i in (*.nupkg) do move /y "%%i" "%LOCALAPPDATA%\Programs\OCTGN\Data\LocalFeed"
pause