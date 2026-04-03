@echo off
title JARVIS AI TERMINAL

color 0B

mode con: cols=90 lines=30

cls

echo.
echo ========================================
echo           JARVIS AI TERMINAL
echo ========================================
echo.

echo STATUS  : Initializing...
timeout /t 1 >nul

cd /d "C:\Users\ABIJITH RAJA B\Desktop\Jarvis"

echo STATUS  : Starting engine...
timeout /t 1 >nul

echo STATUS  : Ready
echo.

.venv\Scripts\python.exe main.py

echo.
echo SYSTEM  : Jarvis stopped.
pause
