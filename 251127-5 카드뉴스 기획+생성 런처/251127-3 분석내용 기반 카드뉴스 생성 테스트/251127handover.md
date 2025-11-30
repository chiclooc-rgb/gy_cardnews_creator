🔄 프로젝트 인수인계서
작성일: 2025-11-27
작성자: Cursor (Antigravity AI)
인수자: Claude Code

📋 프로젝트 개요
프로젝트명
광양시 카드뉴스 자동 생성 시스템 (RAG 기반 AI 디자이너)

목적
광양시청 공지사항을 입력받아 AI가 자동으로 카드뉴스를 기획하고 디자인하는 시스템 구축

주요 기술 스택
언어: Python 3.x
AI 모델: Google Gemini API
text-embedding-004: 스타일 검색용
gemini-3-pro-image-preview: 이미지 생성용
주요 라이브러리:
google-generativeai: Gemini API 연동
numpy: 벡터 연산
PIL (Pillow): 이미지 처리
tkinter: GUI 파일 선택
📂 프로젝트 구조
작업 디렉토리
c:\Users\a\Desktop\작업파일(디자인, AI 등)\251127-3 분석내용 기반 카드뉴스 생성 테스트\
주요 파일 및 디렉토리
📄 핵심 스크립트
test_designer_rag.py
 (433줄, 21KB)

역할: RAG 기반 카드뉴스 이미지 생성기
기능:
기획안 JSON 파일 선택
스타일 색인에서 유사 레퍼런스 검색
Gemini Pro 모델로 이미지 생성
500 에러 재시도 로직 포함
매돌이 캐릭터 조건부 삽입
상태: ✅ 완성 및 테스트 완료
mvp_test.py
 (3.9KB)

역할: 초기 MVP 테스트 스크립트
상태: 참고용 (현재 미사용)
📊 데이터 파일
gwangyang_style_db.jsonl
 (1.1MB)

광양시 카드뉴스 1,600장 분석 데이터
각 이미지의 기획 의도, 스타일, 톤앤매너 정보 포함
gwangyang_style_index.pkl
 (10.2MB)

스타일 검색용 임베딩 색인 파일
build_index.py로 생성됨
📁 디렉토리
매돌이 이미지/

광양시 마스코트 '매돌이' 캐릭터 이미지 저장
자동으로 첫 번째 이미지 로드
완성된 카드뉴스/

생성된 카드뉴스 이미지 저장 위치
현재 36개 이미지 저장됨
파일명 형식: {제목}_{페이지번호}_{타입}.png
📖 문서
guide.md
 (222줄, 9.9KB)
AI 디자이너 사용 가이드
코드 설명 및 실행 방법 포함
🔑 API 키 정보
Google Gemini API
현재 키: AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8
위치: 
test_designer_rag.py
 18번째 줄
티어: Tier 1 (유료)
주의사항:
Rate Limit 방지를 위해 이미지 생성 후 10초 대기
500 에러 발생 시 재시도 로직 구현됨
🚀 실행 워크플로우
1단계: 환경 설정
# 가상환경 활성화 (이미 존재)
.venv\Scripts\activate
# 필요 라이브러리 (이미 설치됨)
pip install google-generativeai numpy pillow
2단계: 카드뉴스 생성 실행
python test_designer_rag.py
3단계: 실행 흐름
비율 선택: 팝업 창에서 1, 2, 3 입력

1: 4:5 (피드 권장)
2: 1:1 (정방형)
3: 9:16 (릴스/스토리)
기획안 선택: JSON 파일 선택 (예: 2025-11-27 광양시 청년 주택자금 대출이자 지원!.json)

매돌이 로드: 매돌이 이미지/ 폴더에서 자동 로드

스타일 검색:

COVER, BODY, OUTRO 타입별로 레퍼런스 검색
상위 15개 후보 중 랜덤 2개 선택 (다양성 확보)
이미지 생성:

페이지별 순차 생성
첫 장 생성 후 확인 요청
나머지 자동 생성 (10초 간격)
결과 저장: 완성된 카드뉴스/ 폴더에 PNG 저장

⚙️ 주요 기능 및 특징
1. RAG 기반 스타일 검색
def find_best_reference_images(index, query_text, page_type, final_k=2):
    # 상위 15개 후보 중 랜덤 2개 선택
    pool_size = min(len(valid_indices), 15)
    top_indices_pool = np.argsort(scores)[-pool_size:][::-1]
    selected_indices = random.sample(list(top_indices_pool), num_to_select)
목적: 스타일 다양성 확보
방식: 상위 후보군에서 랜덤 선택
2. 500 에러 재시도 로직
def generate_image_with_retry(prompt_parts, output_path, aspect_ratio):
    while True:
        try:
            # 이미지 생성 시도
        except Exception as e:
            if "500" in error_msg:
                # 재시도 옵션 제공
                # 3초 대기 후 재시도
목적: 서버 오류 대응
옵션: r(재시도) / s(건너뛰기)
3. 매돌이 캐릭터 조건부 삽입
# 레퍼런스 이미지 스타일 분석 후 조건부 적용
if character_image:
    prompt_parts.append("참조 이미지에 캐릭터가 있으면 매돌이 사용")
    prompt_parts.append("참조 이미지가 텍스트 위주면 캐릭터 미사용")
목적: 스타일 일관성 유지
방식: AI가 레퍼런스 분석 후 자율 판단
4. 페이지 타입별 레퍼런스 캐싱
# 본문 페이지 일관성 확보
ref_images_cache = {}
for page_type in page_types_needed:
    ref_images_cache[page_type] = find_best_reference_images(...)
목적: 본문 페이지 스타일 통일
효과: 모든 BODY 페이지가 동일 레퍼런스 사용
🐛 알려진 이슈 및 해결 방법
1. 스타일 획일화 문제
증상: 생성된 카드뉴스가 너무 비슷함
해결: ✅ 랜덤 선택 로직 추가 (pool_size=15, final_k=2)
위치: 
test_designer_rag.py
 47-100번째 줄
2. 500 에러 빈발
증상: Google 서버 과부하로 생성 실패
해결: ✅ 재시도 로직 + 10초 대기 시간
위치: 
test_designer_rag.py
 122-200번째 줄
3. 매돌이 캐릭터 변형 문제
증상: AI가 매돌이를 새로 그려서 다르게 생김
해결: ✅ 프롬프트에 "절대 변형 금지" 명시
위치: 
test_designer_rag.py
 366-377번째 줄
📊 현재 작업 상태
✅ 완료된 작업
✅ 1,600장 카드뉴스 이미지 분석 및 DB 구축
✅ 스타일 임베딩 색인 생성 (
gwangyang_style_index.pkl
)
✅ RAG 기반 기획안 생성기 구현 (test_planner_rag.py)
✅ RAG 기반 이미지 생성기 구현 (
test_designer_rag.py
)
✅ 스타일 다양성 개선 (랜덤 선택)
✅ 에러 핸들링 강화 (500 에러 재시도)
✅ 매돌이 캐릭터 조건부 삽입
✅ 실제 카드뉴스 36장 생성 테스트 완료
🔄 진행 중인 작업
없음 (시스템 안정화 단계)
📝 향후 개선 과제
프롬프트 최적화

한글 텍스트 가독성 개선
레이아웃 정확도 향상
배치 처리 기능

여러 기획안 일괄 처리
스케줄링 기능
품질 평가 시스템

생성 이미지 자동 평가
재생성 기준 설정
웹 인터페이스

GUI 개선 (tkinter → Streamlit/Gradio)
실시간 미리보기
🔍 중요 코드 위치 참조
핵심 함수 위치 (
test_designer_rag.py
)
함수명	줄 번호	기능
load_index()
37-44	색인 파일 로드
find_best_reference_images()
47-100	RAG 스타일 검색 (랜덤 선택)
get_user_aspect_ratio()
102-119	비율 선택 GUI
generate_image_with_retry()
122-200	이미지 생성 (재시도 로직)
run_rag_designer()
202-421	메인 실행 함수
주요 설정 위치
설정 항목	줄 번호	현재 값
API 키	18	AIzaSy...
색인 파일 경로	23	
gwangyang_style_index.pkl
출력 디렉토리	24	완성된 카드뉴스/
임베딩 모델	30	text-embedding-004
이미지 생성 모델	32	gemini-3-pro-image-preview
후보군 크기	74	pool_size = 15
선택 개수	47	final_k = 2
대기 시간	417	10초
📚 관련 대화 이력
최근 18개 대화 요약
62569e8e (2025-11-27): 스타일 획일화 문제 해결
04145980 (2025-11-27): AI 디자이너 실행 테스트
5c66f93b (2025-11-27): 디자이너 스크립트 개선
d7ed83cf (2025-11-27): RAG 기획자 실행
6d9b82f1 (2025-11-27): RAG 기획자 구현
ecb9e93c (2025-11-27): 광양시 카드뉴스 DB 구축
6591eaac (2025-11-26): 이미지 분류 스크립트
🎯 인수자를 위한 체크리스트
즉시 확인할 사항
 Python 가상환경 활성화 확인 (.venv)
 API 키 유효성 확인
 필수 파일 존재 확인:
 
gwangyang_style_index.pkl
 
gwangyang_style_db.jsonl
 
test_designer_rag.py
 테스트 실행: python test_designer_rag.py
이해해야 할 핵심 개념
RAG (Retrieval-Augmented Generation)

기존 스타일 DB에서 유사 이미지 검색
검색 결과를 프롬프트에 포함하여 생성
임베딩 기반 검색

텍스트를 벡터로 변환
코사인 유사도로 순위 계산
프롬프트 엔지니어링

레퍼런스 이미지 + 텍스트 내용 + 스타일 지시
매돌이 캐릭터 조건부 삽입 로직
주의사항
⚠️ API 사용량 관리

Gemini API는 유료 티어 사용 중
이미지 생성 시 10초 대기 (Rate Limit 방지)
500 에러 시 무한 재시도 방지
⚠️ 파일 경로

한글 경로 사용 중 (작업파일(디자인, AI 등))
경로 변경 시 BASE_DIR 확인 필요
⚠️ 가상환경

.venv 폴더 내 라이브러리 설치됨
새 환경 구축 시 requirements.txt 생성 권장
💡 추가 참고사항
생성된 카드뉴스 예시
현재 완성된 카드뉴스/ 폴더에 다음 주제의 카드뉴스가 저장되어 있음:

광양시 문화대학 강사 모집
광양시 매입임대주택 예비입주자 모집
광양시 청년 주택자금 대출이자 지원
광양시 매돌티콘 공모전
성능 지표
이미지 생성 시간: 페이지당 약 30-60초
스타일 검색 시간: 타입당 약 2-3초
전체 카드뉴스 생성 시간: 7페이지 기준 약 10-15분
비용 추정
임베딩 API: 무료 (일일 한도 내)
이미지 생성 API: 유료 (페이지당 약 $0.XX)
📞 문제 발생 시 대응
자주 발생하는 에러
1. FileNotFoundError: gwangyang_style_index.pkl
원인: 색인 파일 미생성
해결: build_index.py 실행 필요 (현재 없음, 이전 대화에서 생성됨)

2. 500 Internal Server Error
원인: Google 서버 과부하
해결: 스크립트가 자동으로 재시도 옵션 제공

3. API key not valid
원인: API 키 만료 또는 오류
해결: 
test_designer_rag.py
 18번째 줄에서 키 확인

4. 한글 깨짐
원인: 인코딩 문제
해결: 파일 읽기 시 encoding='utf-8' 확인

✅ 인수인계 완료 확인
이 문서를 확인한 후 다음 사항을 테스트하여 인수인계를 완료하세요:

 
test_designer_rag.py
 실행 성공
 카드뉴스 1장 이상 생성 확인
 생성된 이미지 품질 확인
 에러 발생 시 재시도 로직 작동 확인
인수인계 완료일: _____________
인수자 서명: _____________

📌 Note: 이 문서는 Cursor에서 Claude Code로의 원활한 작업 전환을 위해 작성되었습니다.
추가 질문이나 불명확한 부분이 있다면 이전 대화 이력을 참조하세요.