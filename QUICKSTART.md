# 🚀 빠른 시작 가이드

## 1️⃣ 환경 설정 (5분)

### Step 1: Python 패키지 설치
```bash
cd "c:\Users\a\Desktop\작업파일(디자인, AI 등)\251130-2 카드뉴스 생성기 웹앱 구축"
pip install -r requirements.txt
```

### Step 2: Google API Key 준비
1. https://aistudio.google.com/apikey 방문
2. "+ Create API key" 클릭
3. API Key 복사 (나중에 앱 실행 시 필요)

---

## 2️⃣ 로컬 실행 (2분)

### 앱 시작
```bash
streamlit run app.py
```

### 결과
- 브라우저가 자동으로 `http://localhost:8501` 열림
- 이미 GCP API Key를 생성했다면 좌측 사이드바에 입력

---

## 3️⃣ 첫 번째 카드뉴스 생성 (5~10분)

### STEP 1️⃣ 기획안 생성

1. **API Key 입력**
   - 좌측 사이드바의 "API Key 입력" 필드에 복사한 Key 입력
   - ✅ "API 설정 완료" 메시지 확인

2. **공고문 업로드**
   - "📄 공고문 업로드" 클릭
   - 텍스트 파일(.txt) 또는 PDF 선택

3. **기획 설정**
   - 상세도 선택:
     - "간단하게 (1~2장)" ← **처음에는 이것 추천**
     - "자세하게 (여러 장)"

4. **기획 시작**
   - "✨ AI 기획 시작" 버튼 클릭
   - 로그 창에서 진행 상황 모니터링 (1~2분 소요)

5. **결과 확인**
   - "📖 보기" 탭: 읽기 쉬운 형식
   - "⚙️ JSON 원본": 원본 JSON
   - "✏️ 편집": 기획안 수정 가능

### STEP 2️⃣ 디자인 생성

6. **기획안 확정**
   - 필요시 "✏️ 편집" 탭에서 수정 후 저장

7. **비율 선택**
   - "📐 비율 선택":
     - "4:5 (인스타그램)" ← **처음에는 이것 추천**
     - "1:1 (정방형)"
     - "9:16 (릴스/스토리)"

8. **디자인 생성**
   - "🎨 AI 디자인 생성 시작" 클릭
   - 진행 바 모니터링 (페이지당 1~3분)

9. **결과 다운로드**
   - 생성된 이미지 확인
   - "📥 다운로드" 버튼으로 각 이미지 저장

---

## ⚠️ 주의사항

### API Key 보안
- ✅ 이 앱은 BYOK (Bring Your Own Key) 정책 사용
- ✅ API Key는 서버에 저장되지 않음
- ✅ 페이지 새로고침 시 자동 삭제
- ⚠️ API Key를 공개적으로 공유하지 마세요
- ⚠️ 필요시 https://aistudio.google.com/apikey에서 Key 재생성

### 파일 준비
```
필수 파일:
✅ app.py (메인 애플리케이션)
✅ requirements.txt (의존성)
✅ gwangyang_style_index.pkl (스타일 데이터베이스)
   또는
✅ 251127-5 카드뉴스 기획+생성 런처/gwangyang_style_index.pkl
```

---

## 🔧 문제 해결

### "스타일 인덱스를 로드할 수 없습니다"
```bash
# gwangyang_style_index.pkl 파일 확인
ls gwangyang_style_index.pkl

# 없으면 기존 폴더에서 복사
cp "251127-5 카드뉴스 기획+생성 런처/gwangyang_style_index.pkl" .
```

### "API 설정 실패"
- API Key 복사 시 공백 확인
- https://aistudio.google.com/apikey에서 새 Key 생성

### "PDF 처리 타임아웃"
- PDF 파일 크기 확인 (200MB 이하)
- 인터넷 연결 확인

### "이미지 생성 실패"
- 자동 재시도 (최대 3회)
- 계속 실패하면 페이지 건너뛰기 옵션 선택

---

## 📚 다음 단계

- [README.md](./README.md) - 상세 사용 설명서
- [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) - 개발 계획서
- [Streamlit 공식 문서](https://docs.streamlit.io/) - 고급 설정

---

**준비 완료!** 이제 앱을 실행하고 카드뉴스를 생성해보세요! 🎉
