import google.generativeai as genai
from PIL import Image
import os
import io\

# ==========================================
# ⭐⭐⭐ 여기를 수정해주세요! ⭐⭐⭐
# 1. 본인의 구글 API 키
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"

# 2. 레퍼런스로 사용할 이미지의 전체 경로 (아까 테스트 데이터 1번 이미지 경로)
# 예: r"c:\Users\a\Desktop\작업파일\...\imgi_2118_img_l.jpg" (앞에 r을 붙이면 편합니다)
REFERENCE_IMAGE_PATH = r"C:\Users\a\Desktop\작업파일(디자인, AI 등)\251127 카드뉴스 스타일 분석 및 DB 구축(Gemini Vision API)\sorted_output\img\10_gy_cover\imgi_2118_img_l.jpg"
# ====



def run_mvp_test():
    # 1. API 설정 (⭐ Nano Banana Pro 모델로 변경 ⭐)
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # 여기가 핵심! Pro 모델을 사용합니다.
        model = genai.GenerativeModel('gemini-3-pro-image-preview')
        print("✅ 모델 설정 완료: gemini-3-pro-image-preview (Nano Banana Pro)")
    except Exception as e:
        print(f"❌ API 설정 오류: {e}")
        return

    # 2. 레퍼런스 이미지 로드
    if not os.path.exists(REFERENCE_IMAGE_PATH):
        print(f"❌ 오류: 레퍼런스 이미지 파일을 찾을 수 없습니다.\n경로: {REFERENCE_IMAGE_PATH}")
        return
    
    try:
        ref_image = Image.open(REFERENCE_IMAGE_PATH)
        print("✅ 레퍼런스 이미지 로드 완료")
    except Exception as e:
        print(f"❌ 이미지 열기 오류: {e}")
        return

    # 3. 프롬프트 구성
    prompt_parts = [
        "당신은 전문 카드뉴스 디자이너입니다.",
        "제공된 참조 이미지의 **'생동감 있는 초록색 계열 배경과 노란색 포인트' 색감**, **'활기차고 친근한' 분위기**, 그리고 **'좌측 상단 제목 집중 및 우측 하단 캐릭터 배치' 레이아웃**을 완벽하게 참고하여 새로운 카드뉴스 표지를 만들어주세요.",
        ref_image, # 참조 이미지 전송
        "\n\n[새로운 이미지 내용 지시사항]",
        "1. 페이지 타입: COVER (표지)",
        "2. 메인 타이틀: \"광양시, 2026년 청년 면접 정장 무료 대여!\"",
        "3. 서브 타이틀: \"취업 준비 부담 ZERO, 성공 취업 응원합니다\"",
        "4. 필수 요소: 우측 하단에 '매돌이' 캐릭터가 정장을 입고 응원하는 모습을 배치해주세요.",
        "5. 텍스트는 가독성이 매우 좋아야 하며, 한글이 절대 깨지지 않게 자연스럽게 디자인해주세요."
    ]

    print("\n🚀 이미지 생성 요청 중... (Pro 모델이라 시간이 조금 더 걸릴 수 있습니다)")
    try:
        # 4. API 호출
        response = model.generate_content(prompt_parts)
        
        # 5. 결과 처리 및 저장
        generated_image = None
        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    generated_image = Image.open(io.BytesIO(image_data))
                    break
        
        if generated_image:
            output_filename = "mvp_result_pro.png"
            generated_image.save(output_filename)
            print(f"\n🎉 성공! Pro 모델이 이미지를 생성했습니다: {output_filename}")
            print("생성된 이미지를 확인해보세요!")
            os.startfile(output_filename)
        else:
            print("\n⚠️ 생성 실패: API가 이미지를 반환하지 않았습니다.")
            if response.text:
                print(f"응답 내용: {response.text}")

    except Exception as e:
        print(f"\n❌ 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    run_mvp_test()