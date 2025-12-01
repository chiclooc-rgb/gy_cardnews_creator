# 🚀 배포 및 마이그레이션 계획: 카드뉴스 생성기

이 문서는 로컬 테스트 환경의 카드뉴스 생성기를 1600개 이상의 전체 데이터셋을 포함한 프로덕션용 Streamlit 배포 환경으로 마이그레이션하기 위한 단계별 계획입니다.

## 1. 📦 데이터 마이그레이션 (전체 데이터셋)

현재 테스트 버전은 소량의 데이터를 사용 중입니다. 1600개의 전체 이미지 데이터셋을 통합해야 합니다.

### A. 데이터 정리 (Data Organization)
1.  **이미지 디렉토리**: 1600개 이상의 모든 원본 이미지를 하나의 전용 폴더에 모아주세요. 예: `data/images/`.
    *   *용량 확인*: 이미지 전체 용량이 **500MB**를 넘는지 확인하세요.
        *   **옵션 A (1GB 미만 권장)**: GitHub에 그대로 커밋합니다 (표준 방식).
        *   **옵션 B (대용량 파일)**: Git LFS (Large File Storage)를 사용합니다.
        *   **옵션 C (외부 호스팅)**: S3나 Google Drive에 이미지를 호스팅하고, 코드가 URL에서 이미지를 불러오도록 수정합니다 (코드 수정 필요).
2.  **인덱스 재구축 (Rebuild Index)**:
    *   전체 `data/images/` 디렉토리를 대상으로 `build_index.py` (또는 `gwangyang_style_index.pkl` 생성 스크립트)를 실행합니다.
    *   생성된 `.pkl` 또는 `.jsonl` 파일이 1600개 이미지에 대한 메타데이터를 모두 포함하는지 확인합니다.
    *   **조치**: 전체 데이터를 확보한 후 로컬에서 이 작업을 한 번 실행하고, 업데이트된 인덱스 파일을 커밋해야 합니다.

### B. 프로젝트 구조 업데이트
배포를 위한 권장 폴더 구조:
```
/
├── app.py                  # 메인 Streamlit 애플리케이션
├── requirements.txt        # 파이썬 의존성 목록
├── packages.txt            # (선택사항) OS 레벨 의존성
├── .gitignore              # Git 무시 규칙
├── .streamlit/
│   └── secrets.toml        # 로컬 비밀키 (절대 커밋 금지)
├── data/
│   ├── images/             # 전체 이미지 데이터셋
│   └── gwangyang_style_index.pkl # 업데이트된 인덱스 파일
└── styles.css              # 커스텀 CSS
```

## 2. 🛠️ 배포를 위한 코드 수정

### A. API 키 관리 (보안)
현재 앱은 사이드바에서 API 키를 입력받습니다. 더 매끄러운 경험을 위해 다음을 권장합니다:
1.  **Streamlit Secrets 사용**: `st.secrets`를 통해 API 키를 관리합니다.
    *   **로컬 환경**: `.streamlit/secrets.toml` 파일을 생성합니다:
        ```toml
        GOOGLE_API_KEY = "여기에-API-키-입력"
        ```
    *   **프로덕션 (Streamlit Cloud)**: 대시보드의 "Secrets" 설정에 동일한 키를 추가합니다.
2.  **코드 수정**: `app.py`가 `st.secrets`를 먼저 확인하도록 수정합니다.
    ```python
    # 예시 로직
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        # 사이드바 입력으로 대체
    ```

### B. 파일 경로 (File Paths)
*   `app.py`의 모든 파일 경로는 **상대 경로**여야 합니다.
*   현재 코드는 `Path(__file__).parent`를 사용하고 있어 좋습니다.
*   **중요**: `gwangyang_style_index.pkl`에 저장된 `file_path` 정보도 배포 환경과 일치해야 합니다. 만약 로컬 절대 경로(예: `C:/Users/...`)로 인덱스를 만들었다면 서버에서 **오류가 발생**합니다.
*   **해결책**: 인덱스를 재구축할 때 **상대 경로**(예: `data/images/img_001.png`) 또는 파일명만 저장하고, `app.py`에서 전체 경로를 재구성하도록 해야 합니다.

### C. 임시 저장소 주의 (Ephemeral Storage)
*   **Streamlit Cloud는 임시적입니다**: `outputs/` 폴더에 저장된 파일은 앱이 재시작되거나 절전 모드로 들어가면 **사라집니다**.
*   **해결책**:
    *   사용자에게 결과를 즉시 다운로드하도록 유도합니다 (현재 "다운로드" 버튼 기능 유지).
    *   영구 저장이 필요하다면 Google Drive나 AWS S3 연동을 고려해야 합니다 (추후 개선 사항).

## 3. ☁️ 배포 단계 (Streamlit Cloud)

1.  **GitHub에 푸시**:
    *   전체 코드, `requirements.txt`, 그리고 **업데이트된 인덱스 파일**을 커밋합니다.
    *   *참고*: 이미지가 GitHub 용량을 초과하면 옵션 C(외부 호스팅)를 논의해야 합니다.

2.  **Streamlit Cloud에 앱 생성**:
    *   [share.streamlit.io](https://share.streamlit.io/)에 접속합니다.
    *   GitHub 계정을 연동합니다.
    *   리포지토리와 브랜치를 선택합니다.
    *   메인 파일 경로: `app.py`.

3.  **Secrets 설정**:
    *   App Settings > Secrets 메뉴에 API 키를 붙여넣습니다:
        ```toml
        GOOGLE_API_KEY = "AIzaSy..."
        ```

4.  **배포 (Deploy)**: "Deploy" 버튼을 클릭하고 빌드가 완료될 때까지 기다립니다.

## 4. ✅ "완전판" 마이그레이션 체크리스트

- [ ] **데이터 수집**: 1600개 이미지를 하나의 폴더에 모으기.
- [ ] **용량 확인**: 폴더 전체 크기 확인 (GitHub 권장 1GB 미만).
- [ ] **인덱스 재구축**: 상대 경로를 사용하여 `.pkl` 인덱스 파일 다시 생성.
- [ ] **코드 업데이트**:
    - [ ] `app.py`가 `st.secrets`를 사용하도록 수정.
    - [ ] 이미지 로딩 로직이 상대 경로를 올바르게 처리하도록 수정.
- [ ] **로컬 테스트**: 전체 데이터를 사용하여 `streamlit run app.py` 실행 및 성능 확인.
- [ ] **푸시 및 배포**: GitHub에 푸시하고 Streamlit Cloud에 배포.
