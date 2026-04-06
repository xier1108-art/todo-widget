# 📋 할일 위젯 (Todo Widget)

> 포스트잇 스타일의 가벼운 데스크탑 할일 관리 위젯

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-Private-red)

---

## ✨ 주요 기능

- 📌 **항상 위에 고정** — 다른 창 위에 항상 떠있는 위젯
- 🗂 **시스템 트레이** — 닫기 버튼을 눌러도 트레이로 숨겨져 백그라운드에서 계속 실행
- 💾 **자동 저장** — 추가·체크·삭제 즉시 자동으로 저장
- 📅 **미완료 항목 유지** — 날짜가 지나도 완료하지 않은 항목은 사라지지 않음 (`N일 전` 뱃지 표시)
- ✏️ **인라인 편집** — 항목 더블클릭으로 바로 수정
- 🔍 **전체 목록 관리 창** — 필터(전체/미완료/완료) + 검색 기능
- 🎨 **5가지 테마** — 노랑(기본) / 파랑 / 초록 / 분홍 / 다크모드
- 🚀 **시작프로그램 등록** — 윈도우 부팅 시 자동 실행 옵션

---

## 🖥 UI 미리보기

```
┌──────────────────────────────┐
│ 📋 2026.04.06 (월)       ─ × │  ← 드래그로 이동 가능
├──────────────────────────────┤
│ ☐ 회의 자료 준비       (어제)│
│ ☑ 이메일 확인               │  ← 완료 시 취소선
│ ☐ 운동하기                  │
│  2/3 완료   완료삭제   목록  │
├──────────────────────────────┤
│  할일 입력...           [ + ]│
└──────────────────────────────┘
```

---

## 🚀 실행 방법

### 방법 1 — Python으로 바로 실행

```bash
pip install pystray Pillow
python todo_widget.py
```

### 방법 2 — EXE 빌드 후 실행

```bash
pip install pystray Pillow pyinstaller
build.bat
# 또는
pyinstaller --onefile --noconsole --name "할일위젯" todo_widget.py
```

빌드 결과물: `dist/할일위젯.exe`

---

## 📁 파일 구조

```
todo-widget/
├── todo_widget.py   # 메인 소스 코드 (단일 파일)
├── build.bat        # EXE 빌드 스크립트
├── todos.json       # 할일 데이터 (자동 생성)
└── README.md
```

> `todos.json`은 실행 파일과 같은 폴더에 자동으로 생성됩니다.

---

## ⚙️ 사용법

| 동작 | 방법 |
|------|------|
| 할일 추가 | 입력창 타이핑 후 `Enter` 또는 `+` 버튼 |
| 완료 체크/해제 | 항목 클릭 |
| 텍스트 수정 | 항목 **더블클릭** |
| 항목 삭제 | 우측 `×` 버튼 |
| 창 숨기기 | `─` 또는 `×` → 트레이로 최소화 |
| 다시 열기 | 트레이 아이콘 **더블클릭** |
| 설정 변경 | 헤더 **우클릭** 또는 트레이 아이콘 우클릭 |
| 전체 목록 | 하단 `목록` 버튼 |

### 설정 메뉴 (헤더 우클릭)

- ✅ 항상 위에 표시 토글
- 🔆 투명도 조절 (75% / 85% / 95% / 100%)
- 🎨 테마 색상 변경 (노랑★ / 파랑 / 초록 / 분홍 / 다크)
- 🚀 윈도우 시작 시 자동 실행 등록/해제
- 📂 전체 목록 창 열기
- ❌ 완전 종료

---

## 📦 의존성

| 패키지 | 용도 | 설치 필요 |
|--------|------|-----------|
| `tkinter` | GUI 프레임워크 | ❌ Python 내장 |
| `pystray` | 시스템 트레이 아이콘 | ✅ `pip install pystray` |
| `Pillow` | 트레이 아이콘 이미지 생성 | ✅ `pip install Pillow` |
| `pyinstaller` | EXE 빌드 (빌드 시에만) | ✅ `pip install pyinstaller` |

---

## 🗃 데이터 구조 (todos.json)

```json
{
  "window":        { "x": 100, "y": 100, "width": 280, "height": 420 },
  "theme":         "yellow",
  "always_on_top": true,
  "opacity":       0.95,
  "startup":       false,
  "todos": [
    { "id": 1, "text": "회의 자료 준비", "done": false, "created_date": "2026-04-05" },
    { "id": 2, "text": "이메일 확인",    "done": true,  "created_date": "2026-04-06" }
  ]
}
```
