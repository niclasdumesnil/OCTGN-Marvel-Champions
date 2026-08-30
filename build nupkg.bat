@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Compilation OCTGN - Detection Automatique (GUID)
echo ===================================================
echo.

set "TARGET_DIR="

:: 1. Parcours de tous les sous-dossiers dans le dossier courant
for /D %%D in (*) do (
    :: 2. Verification de la presence du fichier definition.xml
    if exist "%%~fD\definition.xml" (
        set "TARGET_DIR=%%~fD"
        goto :compile
    )
)

:: 3. Si la boucle se termine sans rien trouver
echo [ERREUR] Aucun sous-dossier contenant un projet OCTGN ("definition.xml") n'a ete trouve.
echo.
pause
exit /b

:compile
echo Projet trouve dans : "%TARGET_DIR%"
echo.
echo [INFO] Deplacement dans le dossier du projet...

:: On entre dans le dossier du projet
pushd "%TARGET_DIR%"

echo Lancement de o8build...
echo ---------------------------------------------------

:: CORRECTION : On utilise le flag -d requis par o8build
o8build -d .

echo ---------------------------------------------------
:: Verification du resultat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] La compilation a echoue. Verifiez les erreurs de code ci-dessus.
) else (
    echo.
    echo [SUCCES] Compilation terminee ! Le fichier .nupkg a ete genere.
)

:: On revient au dossier parent
popd

echo.
pause