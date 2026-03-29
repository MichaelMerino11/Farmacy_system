@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title Instalador Impresora Termica UTN Laboratorio

echo.
echo ================================================
echo   UTN Laboratorio - Instalador de Impresora
echo ================================================
echo.
echo  ANTES DE CONTINUAR:
echo  1. Conecta la impresora termica por USB
echo  2. Enciendela (luz verde encendida)
echo  3. Presiona cualquier tecla para continuar...
echo.
pause > nul

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Ejecuta como administrador.
    echo Clic derecho en el archivo y selecciona Ejecutar como administrador
    pause
    exit /b 1
)

echo [1/4] Instalando driver...
set DRIVER_DIR=%~dp0driver
if not exist "%DRIVER_DIR%\HPRTMOBILE.inf" (
    echo [ERROR] No se encontro la carpeta driver junto a este archivo.
    pause
    exit /b 1
)

pnputil /add-driver "%DRIVER_DIR%\HPRTMOBILE.inf" /install > nul 2>&1
echo    OK

echo [2/4] Detectando puerto de la impresora...
set PRINTER_PORT=USB001

for %%P in (USB001 USB002 USB003 USB004) do (
    if "!PRINTER_PORT!"=="USB001" (
        powershell -Command "try {  = [System.IO.File]::Open('\\.\ %%P', 'Open', 'Write'); exit 0 } catch { exit 1 }" > nul 2>&1
        if !errorLevel! equ 0 set PRINTER_PORT=%%P
    )
)
echo    Puerto: !PRINTER_PORT!

echo [3/4] Registrando impresora...
powershell -Command "Remove-Printer -Name 'HPRT MPT-II' -ErrorAction SilentlyContinue" > nul 2>&1
powershell -Command "Remove-Printer -Name 'HPRT MPT-II(1)' -ErrorAction SilentlyContinue" > nul 2>&1
powershell -Command "Add-PrinterPort -Name '!PRINTER_PORT!' -ErrorAction SilentlyContinue" > nul 2>&1
powershell -Command "Add-Printer -Name 'HPRT MPT-II' -DriverName 'HPRT MPT-II' -PortName '!PRINTER_PORT!'" > nul 2>&1
echo    OK

echo [4/4] Actualizando configuracion...
set ENV_FILE=%~dp0.env
if exist "!ENV_FILE!" (
    powershell -Command "(Get-Content '!ENV_FILE!') | Where-Object {  -notmatch 'PRINTER_' } | Set-Content '!ENV_FILE!'"
    echo PRINTER_NAME=HPRT MPT-II >> "!ENV_FILE!"
) else (
    echo PRINTER_NAME=HPRT MPT-II > "!ENV_FILE!"
)
echo    OK

echo.
echo ================================================
echo   Instalacion completada exitosamente!
echo   Puerto: !PRINTER_PORT!
echo   Impresora: HPRT MPT-II
echo   Ya puedes abrir UTN_Laboratorio.exe
echo ================================================
echo.
pause
