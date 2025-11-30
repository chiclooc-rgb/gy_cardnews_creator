# -*- coding: utf-8 -*-
"""
🚀 카드뉴스 통합 GUI 런처 v2.0 (최종 완성본)
기획안 생성(Step 1) → 이미지 생성(Step 2)
중간 점검, 재시도, 기획안 수정 기능 포함
"""

import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image
import io
import datetime
import re
import time
import random
import threading
import queue
from pypdf import PdfReader

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
# ==========================================

# ---------------------------------------------------------
# [설정 및 경로]
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"
OUTPUT_DIR_PLAN = BASE_DIR / "카드뉴스 문안"
OUTPUT_DIR_IMAGE = BASE_DIR / "완성된 카드뉴스"
CHAR_DIR = BASE_DIR / "매돌이 이미지"

OUTPUT_DIR_PLAN.mkdir(exist_ok=True)
OUTPUT_DIR_IMAGE.mkdir(exist_ok=True)

# ---------------------------------------------------------
# [AI 모델 설정]
# ---------------------------------------------------------
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    embedding_model = 'models/text-embedding-004'
    # 기획용: Gemini 2.0 Flash
    planner_model = genai.GenerativeModel('gemini-2.0-flash')
    # 디자인용: Gemini 3 Pro Image
    designer_model = genai.GenerativeModel('gemini-3-pro-image-preview')
except Exception as e:
    print(f"❌ API 설정 오류: {e}")
    exit()

# ---------------------------------------------------------
# [공통 유틸리티 함수]
# ---------------------------------------------------------
def load_index():
    """스타일 색인 파일 로드"""
    if not INDEX_FILE.exists():
        return None
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

def get_text_for_search(file_path):
    """파일에서 검색용 텍스트 추출"""
    ext = file_path.suffix.lower()
    text = ""
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    elif ext == '.pdf':
        try:
            reader = PdfReader(file_path)
            for i in range(min(2, len(reader.pages))):
                text += reader.pages[i].extract_text()
        except:
            pass
    return text if text else "광양시 공고문"

def search_rag_references(index, query_text, page_type=None, top_k=3):
    """RAG 검색 (대소문자 무시 & 경로 검증 강화)"""
    try:
        # 1. 쿼리 임베딩
        query_embedding = genai.embed_content(
            model=embedding_model, content=query_text[:1000], task_type="retrieval_query"
        )['embedding']
        query_vec = np.array(query_embedding)

        scores = []
        valid_indices = []

        # 디버깅용: DB에 있는 페이지 타입들을 확인하기 위함
        db_types_seen = set()

        for i, entry in enumerate(index):
            # DB에 저장된 페이지 타입 가져오기
            db_page_type = str(entry['data'].get('page_type', '')).strip().upper()
            db_types_seen.add(db_page_type)

            # Designer 모드일 땐 page_type 필터링 (대소문자 무시 비교)
            if page_type:
                target_type = str(page_type).strip().upper()
                if db_page_type != target_type:
                    scores.append(-1)
                    continue

            # 유사도 계산
            similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
            scores.append(similarity)
            valid_indices.append(i)

        # 검색 결과가 0개일 경우 디버깅 정보 출력
        if not valid_indices:
            if page_type:
                print(f"\n⚠️ [검색 실패] '{page_type}' 타입의 이미지를 DB에서 찾을 수 없습니다.")
                print(f"   (DB에 존재하는 타입들: {db_types_seen})")
            return []

        # 다양성 확보: 상위 N개 중에서 랜덤 선택
        pool_size = min(len(valid_indices), 100 if page_type else 15)
        top_indices = np.argsort(scores)[-pool_size:][::-1]

        selected_indices = random.sample(list(top_indices), min(pool_size, top_k))

        results = []
        for i in selected_indices:
            # 절대 경로 문제가 있을 수 있으므로, 경로 보정 시도
            data = index[i]['data'].copy()

            # 1. DB에 있는 절대 경로 그대로 시도
            original_path = Path(data.get('file_path', ''))

            # 2. 파일 존재 확인 및 경로 보정
            final_path = original_path
            if not final_path.exists():
                # 만약 원래 경로에 없으면, 현재 폴더 주변에서 파일명으로 찾아봄
                file_name = data.get('file_name', '')
                possible_dirs = [
                    BASE_DIR / "sorted_output" / "img" / "10_gy_cover",
                    BASE_DIR / "sorted_output" / "img" / "10_gy_body",
                    BASE_DIR / "sorted_output" / "img" / "10_gy_outro",
                    BASE_DIR / "img" / "10_gy_cover",
                    BASE_DIR / "img" / "10_gy_body",
                    BASE_DIR / "img" / "10_gy_outro",
                ]

                for p_dir in possible_dirs:
                    check_path = p_dir / file_name
                    if check_path.exists():
                        final_path = check_path
                        break

            # 경로 정보를 업데이트해서 반환
            data['file_path'] = str(final_path)
            results.append(data)

        return results

    except Exception as e:
        print(f"❌ 검색 오류: {e}")
        return []

# ---------------------------------------------------------
# [GUI 클래스]
# ---------------------------------------------------------
class CardNewsLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("광양시 AI 카드뉴스 생성기 (v2.0)")
        self.root.geometry("700x900")
        self.root.resizable(False, False)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.input_file_path = tk.StringVar()
        self.plan_json_path = tk.StringVar()
        self.aspect_ratio = tk.StringVar(value="4:5")
        self.char_image_path = None

        # 디자인 프로세스 제어용 변수
        self.stop_design_flag = False
        self.design_thread = None
        self.ask_per_page = False

        # 대화창 통신용 큐
        self.dialog_queue = queue.Queue()

        self.index_data = load_index()
        if not self.index_data:
            messagebox.showwarning("경고", "스타일 색인(gwangyang_style_index.pkl)이 없습니다.\n먼저 build_index.py를 실행해주세요.")

        self.create_widgets()
        self.check_character_image()
        self.check_existing_plans()  # 기존 기획안 확인

    def check_character_image(self):
        """매돌이 캐릭터 이미지 자동 로드"""
        if CHAR_DIR.exists():
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
                files = list(CHAR_DIR.glob(ext))
                if files:
                    self.char_image_path = files[0]
                    self.log(f"✅ 매돌이 캐릭터 로드 완료: {files[0].name}")
                    return
        self.log("ℹ️ 매돌이 이미지를 찾을 수 없습니다. (캐릭터 없이 생성됨)")

    def check_existing_plans(self):
        """기존 기획안 파일 확인 및 Step 2 활성화"""
        if OUTPUT_DIR_PLAN.exists():
            json_files = sorted(list(OUTPUT_DIR_PLAN.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
            if json_files:
                # 가장 최근 파일 자동 선택
                latest_file = json_files[0]
                self.plan_json_path.set(str(latest_file))

                filename = latest_file.name
                self.lbl_plan_status.config(text=f"✅ 기획안: {filename}", foreground="green")
                self.btn_edit_plan.config(state="normal")
                self.btn_design.config(state="normal")

                self.log(f"📄 기존 기획안 발견: {filename}")

                # 여러 개 있으면 선택 옵션 제공
                if len(json_files) > 1:
                    self.log(f"   (총 {len(json_files)}개의 기획안이 있습니다. '기획안 선택'으로 다른 것을 선택할 수 있습니다.)")
                else:
                    self.log(f"   바로 디자인을 시작하거나, '기획안 수정'으로 내용을 확인할 수 있습니다.")

    def select_existing_plan(self):
        """기존 기획안 선택 창"""
        if not OUTPUT_DIR_PLAN.exists():
            messagebox.showwarning("경고", "기획안 폴더가 없습니다.")
            return

        json_files = sorted(list(OUTPUT_DIR_PLAN.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            messagebox.showinfo("정보", "저장된 기획안이 없습니다.\n먼저 기획안을 생성하세요.")
            return

        # 선택 창 생성
        select_window = tk.Toplevel(self.root)
        select_window.title("📄 기획안 선택")
        select_window.geometry("600x400")
        select_window.resizable(True, True)
        select_window.attributes('-topmost', True)

        # 설명 라벨
        tk.Label(
            select_window,
            text="사용할 기획안을 선택하세요:",
            font=("Malgun Gothic", 11, "bold")
        ).pack(pady=10)

        # 리스트박스 (스크롤 포함)
        frame_listbox = tk.Frame(select_window)
        frame_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(frame_listbox)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(
            frame_listbox,
            font=("Malgun Gothic", 10),
            yscrollcommand=scrollbar.set,
            height=12
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        # 파일 목록 추가
        file_info = []
        for i, json_file in enumerate(json_files):
            stat = json_file.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            size = stat.st_size
            display_text = f"[{mtime}] {json_file.name} ({size//1024}KB)"
            listbox.insert(tk.END, display_text)
            file_info.append(json_file)

        # 기본 선택 (최신 파일)
        listbox.selection_set(0)
        listbox.see(0)

        # 확인 버튼
        def confirm_selection():
            selection = listbox.curselection()
            if selection:
                selected_file = file_info[selection[0]]
                self.plan_json_path.set(str(selected_file))

                filename = selected_file.name
                self.lbl_plan_status.config(text=f"✅ 기획안: {filename}", foreground="green")
                self.btn_edit_plan.config(state="normal")
                self.btn_design.config(state="normal")

                self.log(f"\n📄 기획안 변경됨: {filename}")
                select_window.destroy()

        button_frame = tk.Frame(select_window)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="✅ 선택",
            command=confirm_selection,
            font=("Malgun Gothic", 10),
            bg="#00A651",
            fg="white",
            padx=20,
            pady=8
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="❌ 취소",
            command=select_window.destroy,
            font=("Malgun Gothic", 10),
            padx=20,
            pady=8
        ).pack(side="left", padx=5)

    def create_widgets(self):
        """GUI 레이아웃 구성"""
        # 헤더
        header_frame = tk.Frame(self.root, bg="#00A651", height=70)
        header_frame.pack(fill="x", padx=0, pady=0)

        tk.Label(
            header_frame,
            text="📰 GWANGYANG AI CARD NEWS CREATOR",
            font=("Arial", 16, "bold"),
            bg="#00A651",
            fg="white"
        ).pack(pady=10)

        tk.Label(
            header_frame,
            text="기획부터 디자인까지 원클릭 자동화",
            font=("Malgun Gothic", 10),
            bg="#00A651",
            fg="#E0FFE0"
        ).pack(pady=(0, 10))

        # 메인 컨테이너
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)

        # --- STEP 1: 기획 ---
        step1_frame = ttk.LabelFrame(main_frame, text=" STEP 1️⃣  기획안 생성 (Planner) ", padding="10")
        step1_frame.pack(fill="x", pady=10)

        frame_file = ttk.Frame(step1_frame)
        frame_file.pack(fill="x", padx=5, pady=5)

        ttk.Button(frame_file, text="📂 공고문 열기 (TXT/PDF)", command=self.select_file).pack(side="left", padx=5)
        ttk.Label(frame_file, textvariable=self.input_file_path, relief="sunken", foreground="blue").pack(
            side="left", padx=5, fill="x", expand=True
        )

        button_frame_plan = ttk.Frame(step1_frame)
        button_frame_plan.pack(fill="x", padx=5, pady=10)

        self.btn_plan = ttk.Button(button_frame_plan, text="✨ AI 기획 시작", command=self.start_planning, state="disabled")
        self.btn_plan.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(button_frame_plan, text="📋 기획안 선택", command=self.select_existing_plan).pack(side="left", fill="x", expand=True, padx=5)

        # --- STEP 2: 디자인 ---
        step2_frame = ttk.LabelFrame(main_frame, text=" STEP 2️⃣  디자인 생성 (Designer) ", padding="10")
        step2_frame.pack(fill="x", pady=10)

        self.lbl_plan_status = ttk.Label(
            step2_frame,
            text="먼저 기획안을 생성해주세요.",
            foreground="gray"
        )
        self.lbl_plan_status.pack(fill="x", pady=(5, 10))

        # 기획안 수정 버튼
        self.btn_edit_plan = ttk.Button(
            step2_frame,
            text="📝 기획안 내용 수정하기",
            command=self.open_json_editor,
            state="disabled"
        )
        self.btn_edit_plan.pack(fill="x", padx=5, pady=5)

        ttk.Separator(step2_frame, orient="horizontal").pack(fill="x", padx=5, pady=10)

        # 비율 선택
        frame_opt = ttk.Frame(step2_frame)
        frame_opt.pack(fill="x", padx=5, pady=5)

        ttk.Label(frame_opt, text="📐 비율 선택: ").pack(side="left", padx=5)
        ttk.Radiobutton(frame_opt, text="4:5 (인스타그램)", variable=self.aspect_ratio, value="4:5").pack(
            side="left", padx=10
        )
        ttk.Radiobutton(frame_opt, text="1:1 (정방형)", variable=self.aspect_ratio, value="1:1").pack(side="left", padx=10)
        ttk.Radiobutton(frame_opt, text="9:16 (릴스/스토리)", variable=self.aspect_ratio, value="9:16").pack(
            side="left", padx=10
        )

        button_frame_design = ttk.Frame(step2_frame)
        button_frame_design.pack(fill="x", padx=5, pady=10)

        self.btn_design = ttk.Button(
            button_frame_design,
            text="🎨 AI 디자인 생성 시작",
            command=self.start_designing,
            state="disabled"
        )
        self.btn_design.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_stop_design = ttk.Button(
            button_frame_design,
            text="🛑 작업 중단",
            command=self.stop_designing,
            state="disabled"
        )
        self.btn_stop_design.pack(side="left", fill="x", expand=True, padx=5)

        # --- 로그 창 ---
        log_frame = ttk.LabelFrame(main_frame, text=" 📋 실행 로그 ", padding="5")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.log_area = scrolledtext.ScrolledText(log_frame, height=14, font=("Consolas", 9), bg="#F5F5F5")
        self.log_area.pack(fill="both", expand=True)

        # 하단: 경로 정보
        info_frame = tk.Frame(self.root, bg="#ECF0F1")
        info_frame.pack(fill="x", padx=0, pady=0)

        info_text = f"📁 작업 경로: {BASE_DIR}"
        tk.Label(info_frame, text=info_text, font=("Malgun Gothic", 9), bg="#ECF0F1", fg="#34495E").pack(
            anchor="w", padx=15, pady=10
        )

    def log(self, msg):
        """로그 메시지 출력"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_area.see(tk.END)
        self.root.update()

    # ============================================================
    # 기획 로직
    # ============================================================
    def select_file(self):
        """파일 선택"""
        file_path = filedialog.askopenfilename(
            title="분석할 공고문 파일(TXT, PDF)을 선택하세요",
            filetypes=[("Documents", "*.txt;*.pdf"), ("Text files", "*.txt"), ("PDF files", "*.pdf")],
            initialdir=BASE_DIR
        )
        if file_path:
            self.input_file_path.set(file_path)
            self.btn_plan.config(state="normal")
            self.log(f"📂 파일 선택됨: {Path(file_path).name}")

    def start_planning(self):
        """기획 프로세스 시작"""
        if not self.index_data:
            messagebox.showerror("오류", "스타일 DB가 로드되지 않았습니다.")
            return

        self.btn_plan.config(state="disabled")
        self.log("=" * 60)
        self.log("🚀 [STEP 1] 기획 프로세스 시작...")
        self.log("=" * 60)

        threading.Thread(target=self.process_planning, daemon=True).start()

    def process_planning(self):
        """기획 로직 실행 (별도 스레드)"""
        try:
            file_path = Path(self.input_file_path.get())
            ext = file_path.suffix.lower()
            prompt_content = None
            query_text = ""

            # 파일 처리
            if ext == '.txt':
                self.log("📄 텍스트 파일 감지됨.")
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                prompt_content = text
                query_text = text[:500]

            elif ext == '.pdf':
                self.log("📑 PDF 파일 감지됨.")
                self.log("☁️ PDF를 구글 서버로 업로드 중...")

                max_retries = 3
                uploaded_file = None
                for attempt in range(max_retries):
                    try:
                        uploaded_file = genai.upload_file(path=file_path, display_name="Notice PDF")
                        break
                    except Exception as e:
                        self.log(f"⚠️ 업로드 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                        else:
                            raise

                # PDF 상태 확인
                self.log("   (파일 처리 중... 최대 60초 소요)")
                processing_timeout = 60
                start_time = time.time()

                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > processing_timeout:
                        raise Exception(f"PDF 처리 타임아웃 ({processing_timeout}초 초과)")

                    time.sleep(2)
                    try:
                        uploaded_file = genai.get_file(uploaded_file.name)
                    except Exception as e:
                        self.log(f"⚠️ 파일 상태 조회 실패: {e}")
                        time.sleep(2)
                        continue

                if uploaded_file.state.name == "FAILED":
                    raise Exception("PDF 처리 실패 - 파일이 손상되었거나 형식이 올바르지 않습니다.")

                self.log("✅ PDF 업로드 완료.")
                prompt_content = uploaded_file
                query_text = get_text_for_search(file_path)[:500]

            # RAG 검색
            self.log("📚 유사 스타일 검색 중...")
            examples = search_rag_references(self.index_data, query_text, top_k=3)
            example_text = "\n".join([
                json.dumps(
                    {k: v for k, v in ex.items() if k in ['page_type', 'main_title', 'tone_and_manner']},
                    ensure_ascii=False
                )
                for ex in examples
            ])

            # 기획안 작성
            self.log("🧠 AI가 기획안을 작성 중입니다...")

            prompt = [
                "당신은 광양시청 홍보팀 수석 카드뉴스 기획자입니다.",
                "제공된 공고문(텍스트 또는 PDF)을 정밀하게 분석하세요. 특히 PDF의 경우 표(Table)에 담긴 핵심 정보(대상, 금액, 기간 등)를 누락 없이 파악해야 합니다.",
                "\n[참고할 스타일 예시 (유사 기획안들)]",
                example_text,
                "\n[분석할 공고문 원본]",
                prompt_content,
                "\n[지시사항]",
                "1. **구조 판단:** 내용이 단순하면 SINGLE(1장), 복잡하면 MULTI(표지-본문-마무리) 구조로 판단하세요.",
                "2. **내용 요약:** 핵심 정보를 누락 없이, 카드뉴스에 적합한 짧고 명확한 문장으로 요약하세요.",
                "3. **출력 형식:** 반드시 아래 JSON 형식으로만 출력하세요. (마크다운 제외)",
                """{
  "structure_type": "MULTI",
  "plan": {
    "cover": { "main_title": "...", "sub_title": "..." },
    "body": [ { "page": 1, "summary": ["..."] }, ... ],
    "outro": { "contact": "..." }
  },
  "estimated_tone": "(예: 활기찬, 정보성)"
}"""
            ]

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = planner_model.generate_content(prompt)
                    break
                except Exception as e:
                    self.log(f"⚠️ 기획안 생성 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        self.log(f"   {wait_time}초 후 재시도합니다...")
                        time.sleep(wait_time)
                    else:
                        raise Exception(f"기획안 생성 실패 (최대 {max_retries}회 시도)")

            # 응답 처리
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            plan_data = json.loads(response_text)

            # 결과 저장
            try:
                title = plan_data["plan"]["cover"]["main_title"]
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:20]
            except:
                safe_title = "제목없음"

            today = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"{today}_{safe_title}.json"
            save_path = OUTPUT_DIR_PLAN / filename

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)

            self.plan_json_path.set(str(save_path))

            self.log("\n" + "=" * 60)
            self.log("🎉 [성공] 기획안이 완성되었습니다!")
            self.log(f"저장 위치: {save_path}")
            self.log("=" * 60)

            # UI 업데이트
            self.root.after(0, lambda: self.update_ui_after_plan(filename))

        except Exception as e:
            self.log(f"\n❌ 기획 오류: {e}")
            self.root.after(0, lambda: self.btn_plan.config(state="normal"))
            self.root.after(0, lambda: messagebox.showerror("오류", f"기획안 생성 중 오류 발생:\n{e}"))

    def update_ui_after_plan(self, filename):
        """기획 완료 후 UI 업데이트"""
        self.lbl_plan_status.config(text=f"✅ 기획안: {filename}", foreground="green")
        self.btn_edit_plan.config(state="normal")
        self.btn_design.config(state="normal")
        self.btn_plan.config(state="normal")
        messagebox.showinfo("기획 완료", "기획안이 생성되었습니다!\n\n'기획안 수정하기'를 눌러 내용을 확인할 수 있습니다.")

    def open_json_editor(self):
        """기획안 JSON 에디터 창 열기"""
        json_path = self.plan_json_path.get()
        if not json_path or not os.path.exists(json_path):
            messagebox.showwarning("경고", "기획안 파일이 없습니다.")
            return

        editor = tk.Toplevel(self.root)
        editor.title("📝 기획안 수정")
        editor.geometry("700x700")

        # 탭 (원본 / 편집)
        notebook = ttk.Notebook(editor)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # 원본 탭
        frame_view = ttk.Frame(notebook)
        notebook.add(frame_view, text="📄 원본 보기")

        text_view = scrolledtext.ScrolledText(frame_view, font=("Consolas", 10), state="disabled")
        text_view.pack(fill="both", expand=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.dumps(json.load(f), indent=4, ensure_ascii=False)
        text_view.config(state="normal")
        text_view.insert(tk.END, content)
        text_view.config(state="disabled")

        # 편집 탭
        frame_edit = ttk.Frame(notebook)
        notebook.add(frame_edit, text="✏️ 편집")

        text_area = scrolledtext.ScrolledText(frame_edit, font=("Consolas", 10))
        text_area.pack(fill="both", expand=True)
        text_area.insert(tk.END, content)

        def save_edits():
            try:
                data = json.loads(text_area.get("1.0", tk.END).strip())
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("저장", "수정사항이 저장되었습니다.")
                editor.destroy()
            except Exception as e:
                messagebox.showerror("오류", f"JSON 형식이 올바르지 않습니다.\n{e}")

        tk.Button(
            frame_edit,
            text="💾 저장 및 닫기",
            command=save_edits,
            bg="#00A651",
            fg="white",
            font=("Malgun Gothic", 10)
        ).pack(pady=10)

    # ============================================================
    # 디자인 로직
    # ============================================================
    def start_designing(self):
        """디자인 프로세스 시작"""
        self.stop_design_flag = False
        self.ask_per_page = False
        self.btn_design.config(state="disabled")
        self.btn_stop_design.config(state="normal")

        self.log("\n" + "=" * 60)
        self.log("🚀 [STEP 2] 디자인 프로세스 시작...")
        self.log("=" * 60)

        self.design_thread = threading.Thread(target=self.process_design, daemon=True)
        self.design_thread.start()

    def stop_designing(self):
        """진행 중인 API 요청 일시 중지 및 재시도 옵션 제시"""
        answer = messagebox.askyesno("일시 중지", "현재 진행 중인 요청을 취소하고\n같은 페이지를 다시 요청하시겠습니까?")

        if answer:
            self.stop_design_flag = True
            self.log("\n⏹️ 현재 요청을 취소합니다. 페이지를 다시 생성합니다...")
        else:
            self.log("요청 취소가 거부되었습니다. 계속 기다리는 중입니다...")

    def ask_user(self, title, message, choices=None):
        """메인 스레드에서 사용자에게 묻기 (큐 기반)

        Args:
            title: 대화창 제목
            message: 메시지
            choices: None이면 Yes/No, 리스트면 해당 버튼들 표시

        Returns:
            Yes/No 선택시: True/False
            여러 버튼: 선택된 버튼 텍스트
        """
        # 큐를 비운 후 새로 시작
        try:
            while not self.dialog_queue.empty():
                self.dialog_queue.get_nowait()
        except:
            pass

        def show_dialog():
            try:
                if choices is None:
                    # Yes/No 버튼
                    result = messagebox.askyesno(title, message)
                    self.dialog_queue.put(result)
                elif len(choices) == 2:
                    # 맞춤 2개 버튼
                    ans = messagebox.askyesno(title, message)
                    self.dialog_queue.put(choices[0] if ans else choices[1])
                else:
                    # 3개 이상 버튼: 커스텀 창
                    selected = [None]

                    dialog = tk.Toplevel(self.root)
                    dialog.title(title)
                    dialog.geometry("450x200")
                    dialog.resizable(False, False)
                    dialog.attributes('-topmost', True)
                    dialog.grab_set()

                    msg_label = tk.Label(dialog, text=message, font=("Malgun Gothic", 10), wraplength=400, justify="center")
                    msg_label.pack(pady=20, padx=20)

                    button_frame = tk.Frame(dialog)
                    button_frame.pack(pady=10)

                    def on_click(btn_text):
                        selected[0] = btn_text
                        dialog.destroy()

                    for btn_text in choices:
                        tk.Button(
                            button_frame,
                            text=btn_text,
                            command=lambda bt=btn_text: on_click(bt),
                            font=("Malgun Gothic", 9),
                            width=12,
                            bg="#3498DB" if btn_text == choices[0] else "#95A5A6",
                            fg="white"
                        ).pack(side="left", padx=5)

                    dialog.transient(self.root)
                    self.root.wait_window(dialog)
                    self.dialog_queue.put(selected[0])
            except Exception as e:
                self.log(f"⚠️ 대화창 오류: {e}")
                self.dialog_queue.put(None)

        # 메인 스레드에서 대화창 실행
        self.root.after(0, show_dialog)

        # 백그라운드 스레드에서 응답 대기
        try:
            result = self.dialog_queue.get(timeout=60)
            return result if result is not None else (False if choices is None else choices[0])
        except queue.Empty:
            self.log("⚠️ 사용자 응답 타임아웃")
            return False if choices is None else choices[0]

    def ask_start_page(self, total_pages):
        """시작 페이지 선택 (메인 스레드에서 실행)"""
        result = [0]
        top_window = [None]  # 창 참조 저장

        def get_page():
            # 간단한 입력 창 생성
            top = tk.Toplevel(self.root)
            top_window[0] = top
            top.title("시작 페이지 선택")
            top.geometry("400x150")
            top.resizable(False, False)
            top.attributes('-topmost', True)

            tk.Label(top, text=f"몇 번째 페이지부터 생성하시겠습니까?\n(1~{total_pages}, 빈칸이면 1번부터 시작)",
                     font=("Malgun Gothic", 10)).pack(pady=10)

            entry = tk.Entry(top, font=("Malgun Gothic", 12), width=20)
            entry.pack(pady=10)
            entry.focus()

            def submit():
                try:
                    val = entry.get().strip()
                    if not val:
                        result[0] = 0
                    else:
                        page_num = int(val) - 1
                        if 0 <= page_num < total_pages:
                            result[0] = page_num
                        else:
                            messagebox.showerror("오류", f"1부터 {total_pages} 사이의 숫자를 입력해주세요.")
                            return
                    top.destroy()
                except ValueError:
                    messagebox.showerror("오류", "숫자를 입력해주세요.")

            tk.Button(top, text="확인", command=submit, font=("Malgun Gothic", 10)).pack(pady=10)
            entry.bind('<Return>', lambda e: submit())

        self.root.after(0, get_page)

        # 창이 생성될 때까지 잠깐 기다림
        while top_window[0] is None:
            time.sleep(0.05)

        # 창이 닫힐 때까지 대기
        self.root.wait_window(top_window[0])

        return result[0]

    def process_design(self):
        """디자인 로직 실행 (별도 스레드)"""
        try:
            json_path = self.plan_json_path.get()

            with open(json_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)

            tone = plan_data.get("estimated_tone", "광양시 스타일")
            plan = plan_data["plan"]
            ratio = self.aspect_ratio.get()
            base_name = Path(json_path).stem

            # 페이지 목록 구성
            pages = []
            if "cover" in plan:
                pages.append({
                    "type": "COVER",
                    "data": plan["cover"],
                    "suffix": "00_cover"
                })

            if "body" in plan:
                for i, p in enumerate(plan["body"]):
                    pages.append({
                        "type": "BODY",
                        "data": p,
                        "suffix": f"{i+1:02d}_body"
                    })

            if "outro" in plan:
                pages.append({
                    "type": "OUTRO",
                    "data": plan["outro"],
                    "suffix": "99_outro"
                })

            total_pages = len(pages)
            self.log(f"🎨 총 {total_pages}장의 이미지를 생성합니다. (비율 {ratio})")

            # 이어하기 기능: 이미 생성된 파일 확인
            start_index = 0
            for i, page in enumerate(pages):
                out_path = OUTPUT_DIR_IMAGE / f"{base_name}_{page['suffix']}.png"
                if out_path.exists():
                    start_index = i + 1

            # 시작 페이지 선택 로직
            if start_index > 0 and start_index < len(pages):
                if self.ask_user("이어하기", f"이전에 생성된 {start_index}장의 이미지가 있습니다.\n이어서 생성하시겠습니까?"):
                    self.log(f"▶️ {start_index+1}번째 장부터 이어서 생성합니다.")
                else:
                    if self.ask_user("시작점 선택", f"처음부터 다시 생성하시겠습니까?\n(아니오를 누르면 시작 페이지를 선택할 수 있습니다)"):
                        start_index = 0
                        self.log("▶️ 처음부터 다시 생성합니다.")
                    else:
                        start_index = self.ask_start_page(total_pages)
                        self.log(f"▶️ {start_index+1}번째 장부터 생성합니다.")
            else:
                # 생성된 파일이 없으면 시작 페이지 선택
                start_index = self.ask_start_page(total_pages)
                if start_index > 0:
                    self.log(f"▶️ {start_index+1}번째 장부터 생성합니다.")
                else:
                    self.log("▶️ 처음부터 생성합니다.")

            # 페이지별 생성
            for i in range(start_index, len(pages)):
                if self.stop_design_flag:
                    break

                page = pages[i]
                self.log(f"\n[{i+1}/{total_pages}] '{page['type']}' 페이지 생성 시작...")

                # 참조 이미지 검색
                query = f"{tone} 느낌의 {page['type']} 디자인"
                self.log(f"  (잠시만 기다려주세요, '{page['type']}' 스타일을 검색하고 있습니다...)")
                refs = search_rag_references(self.index_data, query, page_type=page['type'], top_k=2)

                ref_images = []
                if refs:
                    self.log(f"🔍 ['{page['type']}' 스타일] 검색 결과:")
                    for r in refs:
                        try:
                            img = Image.open(r['file_path'])
                            ref_images.append(img)
                            self.log(f"  - [선택됨] {Path(r['file_path']).name} (톤: {r.get('tone_and_manner', 'N/A')})")
                        except Exception as e:
                            self.log(f"  ⚠️ 이미지 로드 실패: {e}")
                else:
                    self.log("⚠️ 적절한 레퍼런스 이미지를 찾지 못했습니다. 기본 스타일로 진행합니다.")

                # 프롬프트 구성
                prompt = [
                    "당신은 광양시청의 전문 카드뉴스 디자이너입니다.",
                    f"제공된 참조 이미지들의 **'{tone}' 스타일과 레이아웃**을 완벽하게 반영하여, 아래 텍스트 내용을 담은 새로운 카드뉴스 이미지를 만들어주세요.",
                    f"페이지 타입: {page['type']}",
                    "**[필수 지시사항]**",
                    "1. 텍스트는 반드시 **한글이 깨지지 않게 디자인과 완벽하게 어우러지도록** 크고 명확하게 배치해야 합니다.",
                    "2. 모든 페이지는 일관된 톤앤매너를 유지해야 합니다.",
                    f"3. **이미지 비율은 반드시 '{ratio}'**여야 합니다.",
                ]

                # 매돌이 캐릭터 보호 로직
                if self.char_image_path:
                    try:
                        char_img = Image.open(self.char_image_path)
                        prompt.append("\n**[매돌이 공식 캐릭터 사용 규칙 (매우 중요 - 반드시 준수)]**")
                        prompt.append("✅ 규칙 1: 제공된 매돌이 이미지는 '광양시의 공식 마스코트'입니다.")
                        prompt.append("✅ 규칙 2: 참조 이미지에 캐릭터가 있으면 → 제공된 매돌이 이미지를 그대로 사용하세요.")
                        prompt.append("✅ 규칙 3: 참조 이미지에 캐릭터가 없으면 → 어떤 캐릭터도 추가하지 마세요.")
                        prompt.append("❌ 금지 사항: 절대로 새로운 캐릭터를 그리지 마세요. 절대로 제공된 매돌이를 변형하지 마세요.")
                        prompt.append("❌ 금지 사항: 색상 변경, 모양 변경, 표정 변경, 옷 변경 등 어떤 형태의 변형도 금지됩니다.")
                        prompt.append("❌ 금지 사항: 비슷한 다른 캐릭터를 대신 그리는 것도 금지됩니다.")
                        prompt.append("⚠️ 경고: 위 규칙을 어기면 설계 의도에 심각한 오류가 발생합니다. 반드시 규칙을 따르세요.")
                        prompt.append(char_img)
                    except:
                        pass
                else:
                    prompt.append("\n**[캐릭터 금지 지시사항]**")
                    prompt.append("이 디자인에는 어떠한 인물이나 캐릭터도 등장시키지 마세요.")

                prompt.extend([
                    "\n[들어갈 텍스트 내용]",
                    json.dumps(page['data'], ensure_ascii=False, indent=2),
                    *ref_images
                ])

                # 이미지 생성 (재시도 로직)
                success = False
                retry_count = 0
                max_auto_retries = 3

                while not success:
                    # stop_design_flag가 켜졌으면 이전 요청 취소 표시
                    if self.stop_design_flag:
                        self.stop_design_flag = False  # 플래그 리셋
                        self.log(f"  ⏹️ 요청이 취소되었습니다. 페이지를 다시 생성합니다...")
                        retry_count = 0  # 재시도 카운트 리셋
                        continue  # 다시 요청 시작

                    try:
                        self.log(f"  ㄴ 🎨 AI 디자이너가 이미지를 그리는 중... (비율: {ratio})")
                        self.log("  (이미지 생성 요청을 보냈습니다. 응답을 기다리는 중... 최대 60초 소요)")

                        # 응답 저장용 큐
                        response_queue = queue.Queue()

                        def generate_in_thread():
                            try:
                                resp = designer_model.generate_content(prompt)
                                response_queue.put(resp)
                            except Exception as e:
                                response_queue.put(e)

                        # 별도 스레드에서 API 호출
                        api_thread = threading.Thread(target=generate_in_thread, daemon=True)
                        api_thread.start()

                        # 최대 60초 대기 (타임아웃 설정)
                        try:
                            resp = response_queue.get(timeout=60)
                            if isinstance(resp, Exception):
                                raise resp
                        except queue.Empty:
                            self.log("  ⏹️ 요청 타임아웃! 다시 시도합니다...")
                            retry_count += 1

                            if retry_count >= max_auto_retries:
                                # 사용자에게 선택 제시
                                if self.ask_user("생성 실패", "응답이 없습니다.\n다시 시도하시겠습니까?"):
                                    retry_count = 0
                                    time.sleep(2)
                                    continue
                                else:
                                    break
                            else:
                                time.sleep(3)
                                continue

                        generated_image = None
                        if resp.parts:
                            for part in resp.parts:
                                if part.inline_data:
                                    img = Image.open(io.BytesIO(part.inline_data.data))
                                    generated_image = img
                                    break

                        if generated_image:
                            out_path = OUTPUT_DIR_IMAGE / f"{base_name}_{page['suffix']}.png"

                            # 파일명 중복 처리
                            counter = 1
                            while out_path.exists():
                                out_path = OUTPUT_DIR_IMAGE / f"{base_name}_{page['suffix']}_{counter}.png"
                                counter += 1

                            generated_image.save(out_path)
                            self.log(f"  ㄴ ✅ 이미지 생성 및 저장 완료: {out_path.name}")
                            success = True
                        else:
                            self.log("  ㄴ ⚠️ 생성 실패: API가 이미지를 반환하지 않았습니다.")
                            if self.ask_user("생성 실패", "이미지가 생성되지 않았습니다.\n다시 시도하시겠습니까?"):
                                continue
                            else:
                                break

                    except Exception as e:
                        error_msg = str(e)

                        if "500" in error_msg or "internal" in error_msg.lower():
                            if retry_count < max_auto_retries:
                                self.log(f"  🚨 구글 서버에 일시적인 문제가 발생했습니다 (500 Error).")
                                self.log(f"  🔄 자동 재시도 중... ({retry_count+1}/{max_auto_retries})")
                                retry_count += 1
                                time.sleep(3)
                                continue
                            else:
                                self.log("  ⚠️ 여러 번 재시도했지만 계속 실패합니다.")
                                if self.ask_user("생성 실패", f"서버 오류가 지속됩니다.\n다시 시도하시겠습니까?"):
                                    retry_count = 0
                                    continue
                                else:
                                    break
                        else:
                            self.log(f"  ㄴ ❌ 알 수 없는 오류 발생: {e}")
                            if self.ask_user("생성 실패", f"오류가 발생했습니다:\n{e}\n\n다시 시도하시겠습니까?"):
                                continue
                            else:
                                break

                if not success:
                    self.log(f"  ❌ '{page['type']}' 페이지 생성 실패")
                    if not self.ask_user("계속하기", "이 페이지 생성을 건너뛰고 다음 페이지를 진행하시겠습니까?"):
                        self.log("🛑 작업이 중단되었습니다.")
                        self.stop_design_flag = True
                        break

                # 첫 장 생성 후 확인 (다음 페이지만 or 나머지 모두)
                if i == start_index and success and not self.stop_design_flag:
                    out_path = OUTPUT_DIR_IMAGE / f"{base_name}_{page['suffix']}.png"
                    self.log(f"\n👀 첫 번째 장({out_path.name})이 생성되었습니다. 확인해보세요!")

                    try:
                        os.startfile(out_path)
                    except:
                        pass

                    # 다음 선택: 다음 페이지만 생성 or 나머지 모두 생성
                    if i < len(pages) - 1:  # 마지막 페이지가 아닐 때만 선택지 제시
                        choice = self.ask_user(
                            "첫 장 확인",
                            "결과가 마음에 드시나요?\n\n어떻게 진행할까요?",
                            choices=["📄 다음 페이지만 생성", "🚀 나머지 모두 생성"]
                        )

                        if choice == "📄 다음 페이지만 생성":
                            self.log("📄 다음 페이지를 생성합니다...")
                            self.ask_per_page = True
                        else:  # "🚀 나머지 모두 생성"
                            self.log("🚀 나머지 페이지를 일괄 생성합니다...")
                            self.ask_per_page = False

                # 1장씩 확인 모드에서 각 장 후 확인
                if self.ask_per_page and success and i > start_index and not self.stop_design_flag:
                    out_path = OUTPUT_DIR_IMAGE / f"{base_name}_{page['suffix']}.png"
                    self.log(f"\n📄 [{i+1}/{total_pages}] 장 생성 완료: {out_path.name}")

                    try:
                        os.startfile(out_path)
                    except:
                        pass

                    # 다음 장 진행 여부 (마지막 페이지가 아닐 때만)
                    if i < len(pages) - 1:
                        choice = self.ask_user(
                            "페이지 확인",
                            f"[{i+1}/{total_pages}] 페이지가 완료되었습니다.\n\n다음 페이지를 진행할까요?",
                            choices=["📄 다음 페이지만 생성", "🚀 나머지 모두 생성"]
                        )

                        if choice == "🚀 나머지 모두 생성":
                            self.log("🚀 나머지 페이지를 일괄 생성합니다...")
                            self.ask_per_page = False
                        else:
                            self.log("📄 다음 페이지를 생성합니다...")

                # 서버 과부하 방지용 대기
                if success and i < len(pages) - 1 and not self.stop_design_flag:
                    self.log("\n☕ 구글 서버 과부하 방지를 위해 10초간 휴식합니다... (Rate Limit 예방)")
                    time.sleep(10)

            if not self.stop_design_flag:
                self.log("\n" + "=" * 60)
                self.log("🎉 모든 작업이 완료되었습니다!")
                self.log(f"결과 폴더: {OUTPUT_DIR_IMAGE}")
                self.log("=" * 60)

                self.root.after(0, lambda: messagebox.showinfo("완료", f"모든 이미지 생성이 완료되었습니다!\n\n{OUTPUT_DIR_IMAGE}"))
                self.root.after(0, lambda: os.startfile(OUTPUT_DIR_IMAGE))
            else:
                # 작업 중단된 경우 재시도 옵션 제시
                answer = messagebox.askyesno("작업 중단됨", "지금까지의 작업을 저장했습니다.\n\n계속 작업하시겠습니까?")

                if answer:
                    self.log("\n▶️ 작업을 재개합니다...")
                    self.root.after(0, lambda: self.start_designing())
                else:
                    self.log("✅ 작업이 완료되었습니다.")

            self.root.after(0, lambda: self.btn_design.config(state="normal"))
            self.root.after(0, lambda: self.btn_stop_design.config(state="disabled"))

        except Exception as e:
            self.log(f"\n❌ 디자인 프로세스 오류: {e}")
            self.root.after(0, lambda: self.btn_design.config(state="normal"))
            self.root.after(0, lambda: self.btn_stop_design.config(state="disabled"))
            self.root.after(0, lambda: messagebox.showerror("오류", f"디자인 생성 중 오류 발생:\n{e}"))


# ==========================================
# 🚀 메인 실행
# ==========================================
def main():
    """메인 함수"""
    # 필수 라이브러리 확인
    try:
        import numpy
        import PIL
        import tkinter
    except ImportError:
        print("필요한 라이브러리를 설치합니다...")
        os.system("pip install numpy pillow google-generativeai pypdf")

    root = tk.Tk()
    app = CardNewsLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
