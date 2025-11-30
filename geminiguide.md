📋 Project Brief: 광양시 AI 카드뉴스 생성기 웹앱 전환 (Migration)
1. 프로젝트 개요

현재 상태: 로컬 Python 환경에서 tkinter GUI와 로컬 파일 시스템(C:\...)을 기반으로 작동하는 launcher.py가 완성되어 있음.

목표: 이를 Streamlit 기반의 웹 애플리케이션으로 전환하여 Streamlit Cloud 또는 Render에 배포할 수 있도록 재구축함.

핵심 변경 사항: 로컬 파일 의존성을 제거하고, 데이터는 Supabase 클라우드에 저장하며, 보안을 위해 API Key는 사용자에게 직접 입력받는 방식을 채택함.

2. 기술 스택 (Tech Stack)

Frontend: Streamlit (Python 웹 프레임워크)

Backend/Storage: Supabase (이미지 호스팅 및 메타데이터 저장)

AI Model: Google Gemini API (gemini-2.5-pro, gemini-3-pro-image-preview)

Deploy: Streamlit Cloud (1순위) 또는 Render

3. 데이터 마이그레이션 요구사항 (Data Migration) 현재 로컬에 있는 1,600장의 이미지와 .pkl 인덱스 파일을 클라우드 환경으로 옮겨야 함.

Supabase Storage:

'gwangyang-assets'라는 버킷을 생성했다고 가정함.

로컬의 sorted_output/img/ 폴더 내 모든 이미지와 매돌이 이미지를 Supabase Storage에 업로드하는 **일회성 마이그레이션 스크립트 (migrate_to_supabase.py)**를 작성할 것.

Index Update:

기존 gwangyang_style_index.pkl의 파일 경로(file_path)가 현재는 로컬 경로(C:\...)로 되어 있음.

마이그레이션 시, 이 경로를 Supabase Storage의 Public URL로 변환하여 새로운 인덱스 파일(또는 Supabase DB 테이블)로 저장해야 함.

4. 웹 애플리케이션 기능 요구사항 (app.py) 기존 launcher.py의 로직을 Streamlit 문법으로 변환할 것.

보안 정책 (Security - BYOK):

절대 원칙: Google API Key를 서버 환경변수나 DB에 저장하지 않음.

입력 방식: st.sidebar에 st.text_input(type="password")를 사용하여 사용자에게 직접 키를 입력받음.

데이터 처리: 입력된 키는 st.session_state에만 일시적으로 유지하며, 브라우저 새로고침 시 초기화되도록 함.

기능 흐름:

API Key 입력 확인: 키가 입력되지 않으면 메인 기능을 비활성화하고 경고 메시지 표시.

Step 1 (기획): st.file_uploader로 공고문(TXT/PDF) 업로드 -> 기획안 생성 -> st.json으로 결과 보여주고 st.text_area로 수정 가능하게 함.

Step 2 (디자인): 기획안이 확정되면 비율 선택(Radio button) -> 디자인 생성 버튼 -> 결과 이미지 st.image로 출력 및 다운로드 버튼 제공.

에러 처리: 500 Internal Error 발생 시 st.error와 함께 '재시도 버튼'을 표시하여 사용자가 다시 요청할 수 있도록 함.

5. 배포 준비 (Deployment)

requirements.txt: streamlit, google-generativeai, supabase, pypdf 등 필요한 모든 라이브러리 명시.

secrets.toml (로컬용): Supabase URL과 Key를 관리하는 템플릿 작성.

👉 Cursor에게 요청할 작업:

먼저 로컬 이미지들을 Supabase로 업로드하고 인덱스 경로를 URL로 바꿔주는 migrate_to_supabase.py 스크립트를 작성해줘.

그다음, 위 요구사항을 완벽하게 반영한 웹앱 메인 코드 **app.py**를 작성해줘. (Tkinter 코드는 전부 제거하고 Streamlit으로 대체)