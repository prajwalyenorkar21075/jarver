@echo off
echo ========================================
echo JARVIS Complete System Test
echo ========================================
echo.

cd /d "D:\New folder (4)\jarvis\backend"

echo [1/10] Testing Health Check...
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Health Check) else (echo [FAIL] Health Check)

echo [2/10] Testing Chat Endpoint...
curl -s -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"test\"}]}" >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Chat Endpoint) else (echo [FAIL] Chat Endpoint)

echo [3/10] Testing System Telemetry...
curl -s http://127.0.0.1:8000/api/system/telemetry >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] System Telemetry) else (echo [FAIL] System Telemetry)

echo [4/10] Testing Vision Endpoint (NEW)...
curl -s -X POST http://127.0.0.1:8000/api/vision/analyze -F "file=@NUL" >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Vision Endpoint) else (echo [FAIL] Vision Endpoint)

echo [5/10] Testing Image Generation (NEW)...
curl -s -X POST http://127.0.0.1:8000/api/image/generate -H "Content-Type: application/json" -d "{\"prompt\": \"test\"}" >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Image Generation) else (echo [FAIL] Image Generation)

echo [6/10] Testing Document Analysis (NEW)...
curl -s -X POST http://127.0.0.1:8000/api/document/analyze -F "file=@NUL" >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Document Analysis) else (echo [FAIL] Document Analysis)

echo [7/10] Testing Coding Workspace...
curl -s "http://127.0.0.1:8000/api/coding/workspace/tree?max_depth=1" >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Coding Workspace) else (echo [FAIL] Coding Workspace)

echo [8/10] Testing Skills Registry...
curl -s http://127.0.0.1:8000/api/skills >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Skills Registry) else (echo [FAIL] Skills Registry)

echo [9/10] Testing Memory System...
curl -s http://127.0.0.1:8000/api/memory/state >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Memory System) else (echo [FAIL] Memory System)

echo [10/10] Testing Biometrics...
curl -s http://127.0.0.1:8000/api/biometrics/status >nul 2>&1
if %errorlevel% equ 0 (echo [PASS] Biometrics) else (echo [FAIL] Biometrics)

echo.
echo ========================================
echo Test Complete
echo ========================================
echo.
echo If all tests PASS, restart the backend to activate new endpoints:
echo   cd "D:\New folder (4)\jarvis\backend"
echo   python -m uvicorn app.main:app --reload
echo.
pause
