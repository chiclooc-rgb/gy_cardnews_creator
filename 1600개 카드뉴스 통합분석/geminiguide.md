광양시 카드뉴스 스타일 DB 구축 실행 계획서
본 문서는 1,600장의 광양시 기존 카드뉴스 이미지를 Google Gemini API를 활용하여 심층 분석하고, 이를 기반으로 '광양시 스타일 스마트 DB'를 구축하기 위한 구체적인 실행 계획을 기술한다.

1. 개요 및 목적
목표: 비정형 이미지 데이터인 1,600장의 카드뉴스를 분석하여 기획 의도, 문체 특성, 디자인 패턴 등 핵심 정보를 구조화된 데이터베이스(JSONL 형식)로 변환한다.

활용 방안: 구축된 DB는 향후 AI 기획자 모델의 학습 데이터(In-context Learning examples) 및 스타일 기반 레퍼런스 검색 시스템의 기초 자료로 활용된다.

핵심 기술: Google Gemini 2.5 Flash (Nano Banana) 모델의 멀티모달 분석 능력 활용.

2. 준비 사항 (Prerequisites)
작업 실행 전 다음 사항이 준비되어야 한다.

이미지 데이터: COVER(표지), BODY(본문), OUTRO(마무리)의 3가지 유형으로 분류가 완료된 1,600장의 이미지 폴더.

개발 환경: Python 3.10+ 환경 및 필수 라이브러리(google-generativeai, pillow) 설치 완료.

API 키: 유효한 Google Gemini API 키 확보.

실행 스크립트: 이미지 분석 및 데이터 추출을 수행할 파이썬 코드 (build_db.py 예정).

3. AI 분석 프롬프트 설계
DB의 품질을 결정하는 핵심 요소인 Gemini 분석 프롬프트는 다음과 같이 구성된다.

[시스템 프롬프트 (Persona Definition)]
"당신은 20년 경력의 베테랑 디자인&콘텐츠 분석가입니다. 제공된 카드뉴스 이미지를 심층 분석하여 기획 의도, 텍스트 구성, 디자인 스타일을 완벽하게 파악하고, 이를 기계가 이해할 수 있는 구조화된 데이터로 추출하는 임무를 맡았습니다."

[분석 요청 프롬프트 (Analysis Request)]
각 이미지와 함께 다음 질문을 전송하여 상세 정보를 추출한다.

1. 기본 식별 정보:

page_type: (COVER / BODY / OUTRO 중 택 1, 이미지 내용 기반 판단)

2. 텍스트 콘텐츠 분석 (OCR 및 구조화):

main_title: (가장 핵심적인 대제목 텍스트)

sub_title: (부제 또는 보조 설명 텍스트, 없으면 null)

body_text_summary: (본문 내용의 핵심 요약)

tone_and_manner: (텍스트에서 느껴지는 전반적인 어조. 예: 친근한, 공식적인, 긴급한, 감성적인)

keywords: (콘텐츠를 대표하는 핵심 키워드 3~5개)

3. 디자인 및 스타일 분석 (Visual Analysis):

visual_vibe: (이미지가 주는 시각적 분위기. 예: 활기찬, 차분한, 신뢰감 있는, 경쾌한)

layout_feature: (텍스트와 이미지의 배치 특징. 예: 상단 제목 집중형, 좌우 2단 분할형, 중앙 이미지 강조형)

color_palette_feel: (주요 색상 조합이 주는 느낌. 예: 파란색 계열의 전문성, 노란색/주황색의 따뜻함)

4. 출력 형식 지정:

"위 분석 결과를 반드시 아래와 같은 단일 JSON 객체 형식으로만 출력하시오." (예시 JSON 구조 제공)

4. 실행 프로세스 (Workflow)
파이썬 스크립트(build_db.py)는 다음과 같은 순서로 작동한다.

초기화: Gemini API 설정 및 결과 저장용 파일(gwangyang_cardnews_db.jsonl) 생성.

순회 (Loop): COVER, BODY, OUTRO 각 폴더 내의 모든 이미지 파일을 순차적으로 읽어들인다.

분석 요청:

이미지 파일을 Gemini Pro Vision 모델로 전송한다.

위에서 정의한 [분석 요청 프롬프트]를 함께 전송한다.

데이터 처리 및 저장:

API로부터 반환된 분석 결과(JSON 문자열)를 파싱한다.

파싱된 데이터에 원본 파일명(file_name)과 경로 정보를 추가한다.

최종 데이터를 JSONL 파일에 한 줄씩 추가(append)하여 저장한다.

완료: 모든 이미지 처리가 끝나면 최종 DB 파일 생성을 완료하고 결과 리포트를 출력한다.

5. 예상 결과물 (Output Example)
작업 완료 후 생성될 gwangyang_cardnews_db.jsonl 파일의 예시 데이터는 다음과 같다.

JSON

{"file_name": "cover_2025_youth_support.png", "page_type": "COVER", "main_title": "2025년 광양시 청년 월세 특별 지원!", "sub_title": "최대 12개월, 월 20만원씩 지원합니다", "tone_and_manner": "혜택을 강조하는 활기차고 친근한 어조", "keywords": ["청년 월세", "특별 지원", "주거 안정"], "visual_vibe": "활기찬, 희망적인", "layout_feature": "상단에 크고 굵은 제목 배치, 하단에 밝은 이미지 사용", "color_palette_feel": "파란색 배경에 노란색 포인트로 주목도 높임"}
{"file_name": "body_policy_details.png", "page_type": "BODY", "main_title": "지원 대상 및 신청 방법 안내", "body_text_summary": "만 19~39세 무주택 청년 대상, 소득 기준 중위 150% 이하. 광양시청 홈페이지 온라인 접수.", "tone_and_manner": "정보를 명확하게 전달하는 공식적이고 신뢰감 있는 어조", "visual_vibe": "차분한, 가독성 높은", "layout_feature": "좌측에 소제목 아이콘, 우측에 줄글 형태의 상세 내용 배치", "color_palette_feel": "흰색 배경에 검은색/파란색 텍스트로 깔끔함 강조"}
... (이하 생략) ...
6. 향후 활용 계획
구축된 이 DB는 광양시 AI 홍보 시스템의 핵심 두뇌 역할을 수행한다.

AI 기획 모델 학습: DB의 tone_and_manner와 텍스트 구성 정보를 활용하여, AI가 광양시 특유의 기획 스타일을 학습(In-context Learning)하도록 한다.

스타일 기반 레퍼런스 검색: "활기찬 분위기의 표지"와 같은 사용자 요청 시, DB의 visual_vibe 및 page_type 필드를 검색하여 최적의 레퍼런스 이미지를 즉시 제공한다.