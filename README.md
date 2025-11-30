# 광양시 AI 카드뉴스 생성기 (Streamlit 웹앱)

## 📋 개요

현재 tkinter 기반의 로컬 애플리케이션을 **Streamlit 기반의 클라우드 웹 애플리케이션**으로 전환한 프로젝트입니다.

### ✨ 주요 기능

- **STEP 1️⃣ 기획안 생성**: 공고문(TXT/PDF)을 업로드하면 AI가 자동으로 카드뉴스 기획안 생성
- **STEP 2️⃣ 디자인 생성**: 확정된 기획안을 바탕으로 AI가 최종 이미지 생성
- **보안**: BYOK(Bring Your Own Key) 정책으로 사용자 API Key 관리

---

## 🚀 빠른 시작

### 1️⃣ 환경 설정

#### 필수 요구사항
- Python 3.9 이상
- pip (Python 패키지 관리자)

#### 저장소 클론
```bash
git clone https://github.com/your-username/gwangyang-card-news.git
cd gwangyang-card-news
```

#### 가상 환경 생성 (권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 의존성 설치
```bash
pip install -r requirements.txt
```

### 2️⃣ 스타일 인덱스 준비

카드뉴스 스타일 데이터베이스를 준비합니다.

#### 옵션 A: 로컬 파일 사용 (개발용)
```
기존 폴더/251127-5 카드뉴스 기획+생성 런처/gwangyang_style_index.pkl
또는
현재 폴더/gwangyang_style_index.pkl
```

#### 옵션 B: Supabase 클라우드 (배포용)
```
1. Supabase 계정 생성: https://supabase.com/
2. gwangyang-assets 버킷 생성
3. 이미지 업로드 (migrate_to_supabase.py 스크립트 사용)
```

### 3️⃣ API Key 설정

#### Google API Key 생성
1. https://aistudio.google.com/apikey 접속
2. "Create API key" 클릭
3. API Key 복사

### 4️⃣ 로컬 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며, `http://localhost:8501`에서 앱을 사용할 수 있습니다.

---

## 📖 사용 방법

### STEP 1️⃣: 기획안 생성

1. 좌측 사이드바에서 Google API Key 입력 (비밀번호 입력 형식)
2. 공고문 파일 업로드 (TXT 또는 PDF)
3. 기획 상세도 선택:
   - "간단하게 (1~2장)": 핵심만 압축
   - "자세하게 (여러 장)": 전체 내용 반영
4. "✨ AI 기획 시작" 버튼 클릭
5. 생성된 기획안 확인 및 필요시 수정

### STEP 2️⃣: 디자인 생성

1. STEP 1에서 생성한 기획안이 자동 로드
2. 이미지 비율 선택:
   - 4:5 (인스타그램)
   - 1:1 (정방형)
   - 9:16 (릴스/스토리)
3. "🎨 AI 디자인 생성 시작" 버튼 클릭
4. 생성된 이미지 확인 및 다운로드

### 로그 모니터링

실시간으로 진행 상황을 로그 창에서 확인할 수 있습니다.

---

## 🔐 보안 정책

### BYOK (Bring Your Own Key)

이 앱은 **사용자 입력 방식의 API Key 관리**를 합니다.

#### 원칙
- ❌ **금지**: Google API Key를 서버에 저장
- ✅ **권장**: 사용자가 직접 입력하고 세션에만 임시 보관
- 🔄 **자동**: 페이지 새로고침 시 자동 삭제

#### 라이프사이클
```
1. 사용자가 API Key 입력 (비밀번호 형식)
   ↓
2. st.session_state에 임시 저장
   ↓
3. 현재 세션에서만 사용 가능
   ↓
4. 페이지 새로고침 → 자동 초기화
   ↓
5. 다음 방문 시 다시 입력 필요
```

---

## 📁 프로젝트 구조

```
gwangyang-card-news/
├── app.py                           # 🎯 메인 Streamlit 애플리케이션
├── requirements.txt                 # 의존성 패키지
├── README.md                        # 이 파일
├── DEVELOPMENT_PLAN.md             # 개발 계획서
├── migrate_to_supabase.py           # Supabase 마이그레이션 스크립트
├── .streamlit/
│   ├── config.toml                 # Streamlit 설정
│   ├── secrets.toml.example        # 시크릿 템플릿 (실제 파일은 따로)
│   └── secrets.toml                # ⚠️ .gitignore에 포함됨
├── .gitignore                       # Git 무시 파일
├── gwangyang_style_index.pkl       # 스타일 데이터베이스 (pickle)
└── 기존 폴더들 (보관용)
    ├── 251127 카드뉴스 스타일 분석...
    └── 251127-5 카드뉴스 기획+생성 런처
```

---

## 🛠️ 문제 해결

### Q1: "스타일 인덱스를 로드할 수 없습니다"

**원인**: gwangyang_style_index.pkl 파일을 찾지 못함

**해결**:
```bash
# 옵션 1: 파일이 있는지 확인
ls gwangyang_style_index.pkl

# 옵션 2: 기존 폴더에서 복사
cp "251127-5 카드뉴스 기획+생성 런처/gwangyang_style_index.pkl" .
```

### Q2: "API 설정 실패"

**원인**: 유효하지 않은 Google API Key

**해결**:
1. https://aistudio.google.com/apikey에서 새 Key 생성
2. API Key 확인 후 다시 입력
3. 복사 시 공백이 없는지 확인

### Q3: "PDF 처리 타임아웃"

**원인**: 파일이 너무 크거나 네트워크 느림

**해결**:
- PDF 파일 크기 확인 (200MB 이하)
- 인터넷 연결 확인
- 다시 시도

### Q4: "이미지 생성에 실패했습니다"

**원인**: API 속도 제한 또는 일시적 서버 오류

**해결**:
- "다시 시도" 버튼 클릭
- 최대 3회까지 자동 재시도
- 여전히 실패하면 페이지 건너뛰기 옵션 선택

---

## 🌐 클라우드 배포

### Streamlit Cloud (권장)

#### 1단계: GitHub 저장소 생성
```bash
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

#### 2단계: Streamlit Cloud 배포
1. https://share.streamlit.io/ 접속
2. "New app" 클릭
3. GitHub 저장소 선택
4. 분기: `main`, 파일: `app.py`

#### 3단계: 환경변수 설정 (필요시)
- Streamlit Cloud 대시보드 → Settings
- Secrets 항목에 필요한 값 추가

### Render (대안)

render.yaml 파일을 작성하고 Render 대시보드에서 배포합니다.

```yaml
services:
  - type: web
    name: gwangyang-card-news
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py
```

---

## 📊 성능 및 제한사항

### 제한사항
- **파일 크기**: 최대 200MB
- **생성 시간**: 페이지당 1~3분
- **동시 사용자**: Streamlit Cloud (1~5명 권장)
- **Rate Limit**: Google Gemini API 정책 준수

### 최적화 팁
- PDF는 첫 2페이지만 분석 (검색 시간 단축)
- 기획안은 미리 작성 후 수정 모드 활용
- 페이지 간격: 자동 5~10초 대기 (서버 부하 방지)

---

## 📞 지원 및 문의

### 문서
- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Google Generative AI 가이드](https://ai.google.dev/)
- [개발 계획서](./DEVELOPMENT_PLAN.md)

### 버그 리포트
이슈를 GitHub에 등록해주세요.

---

## 📜 라이선스

이 프로젝트는 광양시청의 내부 프로젝트입니다.

---

## 🔄 변경 이력

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| v1.0 | 2025-11-30 | Streamlit 웹앱 초기 버전 |

---

**마지막 업데이트**: 2025-11-30
**상태**: 개발 중
