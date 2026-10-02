@echo off
title JARVIS System Shutdown
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_jarvis.ps1"
