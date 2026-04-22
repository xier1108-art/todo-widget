@echo off
chcp 65001 > nul
echo.
echo ====================================================
echo   할일위젯 v4.2.0  EXE 빌드  (PyQt6)
echo ====================================================
echo.

:: PyQt6 설치 확인
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [설치 중] PyQt6 설치...
    pip install PyQt6
)

:: PyInstaller 설치 확인
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [설치 중] PyInstaller 설치...
    pip install pyinstaller
)

echo.
echo [빌드 중] 할일위젯.exe 생성 중...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --icon=icon.ico ^
    --name "할일위젯" ^
    main.py

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패. 위 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   완료! dist\할일위젯.exe 에 저장되었습니다.
echo   todos.json 파일은 exe 와 같은 폴더에 자동 생성됩니다.
echo ====================================================
echo.
pause
