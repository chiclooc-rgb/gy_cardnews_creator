# -*- coding: utf-8 -*-
"""
🚀 카드뉴스 생성기 Streamlit 웹앱 v1.0
기획안 생성(Step 1) → 이미지 생성(Step 2)
로컬 파일 시스템 → 클라우드 마이그레이션 버전
"""

import streamlit as st
import google.generativeai as genai
from pathlib import Path
import json
import io
import pickle
import numpy as np
import time
import random
import re
from datetime import datetime
from PIL import Image
from pypdf import PdfReader
import tempfile
import os
import requests

# ==========================================
# ⚙️ 페이지 설정
# ==========================================
st.set_page_config(
        page_title="광양시 카드뉴스 생성기",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
)

# CSS 커스터마이징 (외부 파일에서 로드)
try:
    css_file = Path(__file__).parent / "styles.css"
    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ styles.css 파일을 찾을 수 없습니다.")
except Exception as e:
    st.warning(f"⚠️ CSS 로드 실패: {e}")

# ==========================================
# 🔧 세션 상태 초기화
# ==========================================
if "google_api_key" not in st.session_state:
        st.session_state.google_api_key = None
if "planner_model" not in st.session_state:
        st.session_state.planner_model = None
if "designer_model" not in st.session_state:
        st.session_state.designer_model = None
if "plan_data" not in st.session_state:
        st.session_state.plan_data = None
if "log_messages" not in st.session_state:
        st.session_state.log_messages = []
if "index_data" not in st.session_state:
        st.session_state.index_data = None
if "design_pages" not in st.session_state:
        st.session_state.design_pages = None
if "current_page_idx" not in st.session_state:
        st.session_state.current_page_idx = 0
if "generated_design_images" not in st.session_state:
        st.session_state.generated_design_images = []
if "design_aspect_ratio" not in st.session_state:
        st.session_state.design_aspect_ratio = "4:5"
if "auto_generate_all" not in st.session_state:
        st.session_state.auto_generate_all = False
if "generation_result" not in st.session_state:
        st.session_state.generation_result = None
if "current_zoom_image" not in st.session_state:
        st.session_state.current_zoom_image = None

# 👇 [추가] 저장 경로 설정 (없으면 생성)
if "output_dir" not in st.session_state:
        # outputs/20240520_143000/ 같은 형식으로 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = Path("outputs") / timestamp
        base_dir.mkdir(parents=True, exist_ok=True)
        st.session_state.output_dir = base_dir
        # add_log는 함수 정의 후에 호출되므로 여기서는 로그를 나중에 추가

# ==========================================
# 📚 유틸리티 함수 (먼저 정의)
# ==========================================
def add_log(msg, indent=0):
        """로그 메시지 추가 (개선된 포맷팅)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        indent_str = "  " * indent
        log_entry = f"[{timestamp}] {indent_str}{msg}"
        st.session_state.log_messages.append(log_entry)

def display_logs():
        """로그 표시 (개선된 형식)"""
        if not st.session_state.log_messages:
            st.info("아직 실행 로그가 없습니다.")
            return

        log_text = "\n".join(st.session_state.log_messages[-100:])  # 최근 100개 표시
        st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

def get_image_download_data(image):
        """이미지를 PNG 바이트로 변환"""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

def load_global_gallery_images():
        """outputs 폴더 내의 모든 PNG 파일을 최신순으로 로드"""
        base_path = Path("outputs")
        if not base_path.exists():
            return []
        
        # 하위 폴더까지 모두 검색하여 .png 파일 찾기
        all_files = list(base_path.glob("**/*.png"))
        
        # 수정 시간 역순(최신순) 정렬
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return all_files

# 🟢 [NEW] 이미지 팝업 함수 (Streamlit 1.28 호환 버전)
def show_image_modal(file_path):
        """이미지를 크게 보여주기 위해 세션 상태에 저장"""
        st.session_state.current_zoom_image = str(file_path)

def load_style_index():
        """스타일 인덱스 로드 (JSON, JSONL 또는 pickle)"""
        try:
            # 현재 앱의 디렉토리 기준
            if '__file__' in globals():
                base_dir = Path(__file__).resolve().parent
            else:
                base_dir = Path.cwd()

            add_log(f"📂 인덱스 검색 시작 (기본 디렉토리: {base_dir})")

            # 검색할 경로들 (우선순위 순)
            index_paths = [
                base_dir / "gwangyang_style_db.jsonl",
                base_dir / "gwangyang_style_index.json",
                base_dir / "gwangyang_style_index.pkl",
                base_dir / "251127-5 카드뉴스 기획+생성 런처" / "gwangyang_style_db.jsonl",
                base_dir / "251127-5 카드뉴스 기획+생성 런처" / "gwangyang_style_index.pkl",
                base_dir.parent / "gwangyang_style_index.pkl",
                base_dir.parent / "251127-5 카드뉴스 기획+생성 런처" / "gwangyang_style_db.jsonl",
                base_dir.parent / "251127-5 카드뉴스 기획+생성 런처" / "gwangyang_style_index.pkl",
            ]

            add_log(f"📂 현재 디렉토리: {base_dir}")
            add_log(f"🔍 스타일 인덱스 검색 중...")

            for index_path in index_paths:
                add_log(f"  ├─ {index_path}")
                if index_path.exists():
                    add_log(f"  ✅ 발견!")

                    # JSONL 파일 (한 줄씩 JSON)
                    if index_path.suffix == ".jsonl":
                        add_log(f"  📖 JSONL 파일 로드 중...")
                        data = []
                        with open(index_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    data.append(json.loads(line))
                        add_log(f"  ✅ JSONL 파일 로드 완료: {len(data)}개 항목")
                        if data:
                            add_log(f"  📋 첫 번째 항목 구조: {list(data[0].keys())}")
                        return data

                    # JSON 파일
                    elif index_path.suffix == ".json":
                        add_log(f"  📖 JSON 파일 로드 중...")
                        with open(index_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        add_log(f"  ✅ JSON 파일 로드 완료 (타입: {type(data).__name__})")
                        if isinstance(data, list):
                            add_log(f"  📋 항목 수: {len(data)}")
                        return data

                    # Pickle 파일
                    elif index_path.suffix == ".pkl":
                        add_log(f"  📦 Pickle 파일 로드 중...")
                        with open(index_path, 'rb') as f:
                            data = pickle.load(f)
                        add_log(f"  ✅ Pickle 파일 로드 완료 (타입: {type(data).__name__})")
                        if isinstance(data, list):
                            add_log(f"  📋 항목 수: {len(data)}")
                        return data

            add_log(f"❌ 파일을 찾을 수 없습니다.")
            return None
        except Exception as e:
            add_log(f"❌ 인덱스 로드 실패: {e}")
            return None

def search_rag_references(index, query_text, page_type=None, top_k=3, color_filter=None):
        """RAG 검색"""
        try:
            if not index:
                add_log(f"⚠️ 검색 실패: 인덱스가 비어있음", indent=2)
                return []

            add_log(f"🔍 RAG 검색 중... (인덱스 크기: {len(index)}, 페이지 타입: {page_type})", indent=2)

            # 쿼리 임베딩
            add_log(f"📌 쿼리 임베딩 생성 중...", indent=2)
            try:
                query_embedding = genai.embed_content(
                    model='models/text-embedding-004',
                    content=query_text[:1000],
                    task_type="retrieval_query"
                )['embedding']
                add_log(f"✅ 임베딩 생성 완료 (크기: {len(query_embedding)})", indent=2)
            except Exception as embed_err:
                add_log(f"❌ 임베딩 생성 실패: {embed_err}", indent=2)
                return []

            query_vec = np.array(query_embedding)

            scores = []
            valid_indices = []

            add_log(f"🔎 인덱스 검색 시작 (총 {len(index)}개 항목 검사 중)...", indent=2)

            for i, entry in enumerate(index):
                # 페이지 타입 필터링
                if page_type:
                    db_page_type = str(entry.get('page_type', '')).strip().upper() if isinstance(entry, dict) else ""
                    target_type = str(page_type).strip().upper()
                    if db_page_type != target_type:
                        scores.append(-1)
                        continue

                # 유사도 계산 (임베딩 있으면)
                if 'embedding' in entry and isinstance(entry['embedding'], list):
                    entry_vec = np.array(entry['embedding'])
                    similarity = np.dot(query_vec, entry_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(entry_vec) + 1e-10)
                    scores.append(similarity)
                    valid_indices.append(i)
                else:
                    scores.append(0)
                    valid_indices.append(i)

            if not valid_indices:
                add_log(f"⚠️ 검색 결과 없음: 일치하는 항목이 없음", indent=2)
                return []

            add_log(f"✅ 유사도 계산 완료 (유효 항목: {len(valid_indices)}개)", indent=2)

            # 상위 선택
            pool_size = min(len(valid_indices), 100 if page_type else 15)
            add_log(f"🎯 상위 결과 선택 중 (pool_size: {pool_size}, top_k: {top_k})...", indent=2)

            if len(scores) > 0:
                top_indices = np.argsort(scores)[-pool_size:][::-1]
                selected_indices = random.sample(list(top_indices), min(len(top_indices), top_k))
                top_scores = sorted(scores, reverse=True)[:pool_size]
                add_log(f"📊 상위 유사도 점수: {[f'{s:.3f}' for s in top_scores[:3]]}", indent=2)
            else:
                selected_indices = list(range(min(top_k, len(valid_indices))))

            results = []
            for idx, i in enumerate(selected_indices):
                entry = index[i]
                if isinstance(entry, dict):
                    data = entry.copy()
                    file_path = data.get('file_path', 'N/A')
                    page_type_val = data.get('page_type', 'N/A')
                    add_log(f"  [{idx+1}] {page_type_val} - {Path(str(file_path)).name if file_path != 'N/A' else 'N/A'}", indent=2)
                else:
                    data = entry
                results.append(data)

            add_log(f"✅ RAG 검색 완료: {len(results)}개 결과 반환", indent=2)
            return results

        except Exception as e:
            add_log(f"❌ 검색 오류: {e}")
            return []

def render_plan_text(data):
        """기획안을 순수 한글 문안으로 변환"""
        if not isinstance(data, dict) or 'structure_type' not in data:
            return "데이터가 없습니다."

        plan = data.get('plan', {})
        lines = []

        # 표지
        if 'cover' in plan:
            cover = plan['cover']
            main_title = cover.get('main_title', '')
            sub_title = cover.get('sub_title', '')

            lines.append(main_title)
            if sub_title:
                lines.append(sub_title)
            lines.append("")

        # 본문
        if 'body' in plan:
            for i, page in enumerate(plan['body'], 1):
                lines.append(f"[페이지 {i}]")
                summary = page.get('summary', [])
                if isinstance(summary, list):
                    for text in summary:
                        lines.append(text)
                else:
                    lines.append(str(summary))
                lines.append("")

        # 마무리
        if 'outro' in plan:
            lines.append("[마무리]")
            outro = plan['outro']
            if isinstance(outro, dict):
                for k, v in outro.items():
                    lines.append(f"{v}")
            else:
                lines.append(str(outro))

        return "\n".join(lines)

def edit_plan_form():
        """기획안 수정 폼 UI (폼 기반)"""
        if st.session_state.plan_data is None:
            return

        st.markdown("#### ✏️ 기획안 편집")
        st.info("👇 각 필드를 직접 수정하세요. 비개발자도 쉽게 편집할 수 있습니다.")

        plan = st.session_state.plan_data.get('plan', {})

        # 1. 표지 편집
        st.markdown("##### 🎯 표지 (COVER)")
        col1, col2 = st.columns(2)

        cover = plan.get('cover', {})
        with col1:
            new_main_title = st.text_input(
                "메인 제목",
                value=cover.get('main_title', ''),
                key="form_cover_main_title"
            )
        with col2:
            new_sub_title = st.text_input(
                "부제목",
                value=cover.get('sub_title', ''),
                key="form_cover_sub_title"
            )

        # 2. 구조 선택
        st.markdown("##### 📐 구조 설정")
        col1, col2 = st.columns(2)

        with col1:
            structure_type = st.selectbox(
                "구조 유형",
                ["SINGLE", "MULTI"],
                index=0 if st.session_state.plan_data.get('structure_type') == 'SINGLE' else 1,
                key="form_structure_type"
            )

        with col2:
            tone = st.text_input(
                "예상 톤",
                value=st.session_state.plan_data.get('estimated_tone', ''),
                key="form_tone"
            )

        # 3. 본문 편집
        st.markdown("##### 📝 본문 (BODY)")
        body = plan.get('body', [])

        body_pages = []
        pages_to_delete = []

        for page_idx, page_data in enumerate(body):
            col_header, col_delete = st.columns([4, 1])

            with col_header:
                st.markdown(f"**페이지 {page_idx + 1}**")

            with col_delete:
                if st.button("🗑️ 삭제", key=f"btn_delete_body_{page_idx}", use_container_width=True):
                    pages_to_delete.append(page_idx)

            # 요약 텍스트 편집
            summary_list = page_data.get('summary', [])
            if isinstance(summary_list, list):
                summary_text = "\n".join(summary_list)
            else:
                summary_text = str(summary_list)

            new_summary_text = st.text_area(
                f"페이지 {page_idx + 1} 요약",
                value=summary_text,
                height=80,
                key=f"form_body_summary_{page_idx}"
            )

            # 요약을 다시 리스트로 변환
            new_summary = [line.strip() for line in new_summary_text.split('\n') if line.strip()]

            page_copy = page_data.copy()
            page_copy['summary'] = new_summary
            body_pages.append(page_copy)

            st.divider()

        # 삭제된 페이지 처리
        if pages_to_delete:
            body_pages = [page for i, page in enumerate(body_pages) if i not in pages_to_delete]

        # 4. 마무리 편집
        st.markdown("##### 👋 마무리 (OUTRO)")
        outro = plan.get('outro', {})

        col_header, col_delete = st.columns([4, 1])
        with col_header:
            st.write("")  # 공간 맞추기
        with col_delete:
            delete_outro = st.checkbox("🗑️ 삭제", key="checkbox_delete_outro")

        outro_fields = {}
        if not delete_outro:
            for key, value in outro.items():
                new_value = st.text_input(
                    key.replace('_', ' ').title(),
                    value=str(value),
                    key=f"form_outro_{key}"
                )
                outro_fields[key] = new_value
        else:
            st.info("💡 마무리 페이지가 제거됩니다.")

        # 저장 버튼
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 수정사항 저장", key="btn_save_plan_form", use_container_width=True, type="primary"):
                # 기획안 재구성
                plan_dict = {
                    "cover": {
                        "main_title": new_main_title,
                        "sub_title": new_sub_title
                    },
                    "body": body_pages
                }

                # 마무리 페이지 포함 여부
                if not delete_outro and outro_fields:
                    plan_dict["outro"] = outro_fields

                new_plan_data = {
                    "structure_type": structure_type,
                    "plan": plan_dict,
                    "estimated_tone": tone
                }

                st.session_state.plan_data = new_plan_data
                st.success("✅ 기획안이 저장되었습니다!")
                time.sleep(1)
                st.rerun()

        with col2:
            if st.button("🔄 취소", key="btn_cancel_plan_form", use_container_width=True):
                st.info("📌 변경사항이 취소되었습니다.")
                time.sleep(1)
                st.rerun()

def generate_single_page_design(page_idx, pages, tone, ratio, cover_color_palette=None):
        """단일 페이지 디자인 생성 함수 (본문 스타일 공유 수정판)"""
        try:
            page = pages[page_idx]

            add_log(f"\n[{page_idx+1}/{len(pages)}] '{page['type']}' 페이지 생성 시작...", indent=0)

            # 1. RAG 검색 (본문은 레퍼런스 공유)
            refs = []
            
            # 인덱스 상태 확인
            if st.session_state.index_data is None:
                add_log(f"⚠️ 인덱스 데이터가 없습니다!", indent=1)
                return None, cover_color_palette

            # BODY 페이지인 경우
            if page['type'] == 'BODY':
                # 이미 저장된 본문용 레퍼런스가 있는지 확인
                if "shared_body_refs" in st.session_state and st.session_state.shared_body_refs:
                    refs = st.session_state.shared_body_refs
                    add_log(f"🔄 [본문 통일] 기존 본문 레퍼런스 {len(refs)}개를 재사용합니다.", indent=1)
                else:
                    # 없으면 새로 검색하고 저장
                    query = f"{tone} 느낌의 {page['type']} 디자인"
                    add_log(f"📚 RAG 검색 시작 - 쿼리: '{query}'", indent=1)
                    
                    refs = search_rag_references(
                        st.session_state.index_data,
                        query,
                        page_type=page['type'],
                        top_k=2
                    )
                    # 검색 결과를 세션에 저장 (다음 BODY 페이지들이 쓰도록)
                    if refs:
                        st.session_state.shared_body_refs = refs
                        add_log(f"💾 본문 레퍼런스 공유를 위해 저장 완료", indent=1)
            
            # COVER나 OUTRO인 경우 (각자 검색)
            else:
                query = f"{tone} 느낌의 {page['type']} 디자인"
                add_log(f"📚 RAG 검색 시작 - 쿼리: '{query}'", indent=1)
                
                refs = search_rag_references(
                    st.session_state.index_data,
                    query,
                    page_type=page['type'],
                    top_k=2
                )

            # 2. 인덱스 상태 확인 및 로그
            if refs:
                add_log(f"✅ 레퍼런스 준비 완료: {len(refs)}개 사용", indent=1)
            else:
                add_log(f"⚠️ 검색 결과 없음 - 기본 레퍼런스 없이 진행", indent=1)

            # COVER 페이지면 색상팔레트 추출
            if page['type'] == 'COVER' and refs and len(refs) > 0:
                retrieved_palette = refs[0].get('color_palette_feel', tone) if isinstance(refs[0], dict) else tone
                add_log(f"🎨 색상 팔레트 저장됨: {retrieved_palette}", indent=1)
                cover_color_palette = retrieved_palette

            # 3. 참조 이미지 로드 (파일 경로 -> 이미지 객체)
            ref_images = []
            if refs:
                add_log(f"🖼️ 참조 이미지 로드 시작:", indent=1)
                for idx, r in enumerate(refs):
                    try:
                        if isinstance(r, dict) and 'file_path' in r:
                            file_path = r['file_path']
                            
                            # URL인 경우 (Supabase)
                            if str(file_path).startswith("http"):
                                try:
                                    response = requests.get(file_path, timeout=10)
                                    response.raise_for_status()
                                    img = Image.open(io.BytesIO(response.content))
                                    ref_images.append(img)
                                    add_log(f"✅ [{idx+1}] 로드 완료 (URL): {Path(file_path).name} ({img.size})", indent=2)
                                except Exception as e:
                                    add_log(f"❌ [{idx+1}] URL 로드 실패: {e}", indent=2)
                            
                            # 로컬 파일인 경우
                            elif Path(file_path).exists():
                                img = Image.open(file_path)
                                ref_images.append(img)
                                add_log(f"✅ [{idx+1}] 로드 완료 (로컬): {Path(file_path).name} ({img.size})", indent=2)
                            else:
                                add_log(f"❌ [{idx+1}] 파일 없음: {file_path}", indent=2)
                        else:
                            add_log(f"⚠️ [{idx+1}] 유효하지 않은 형식", indent=2)
                    except Exception as e:
                        add_log(f"❌ [{idx+1}] 이미지 로드 실패: {e}", indent=2)

            # 4. 프롬프트 구성
            add_log(f"📝 프롬프트 구성 시작 (비율: {ratio}, 톤: {tone})", indent=1)

            prompt_parts = [
                "당신은 광양시청의 전문 카드뉴스 디자이너입니다.",
                f"제공된 참조 이미지들의 스타일과 레이아웃을 반영하여, 아래 텍스트 내용을 담은 새로운 카드뉴스 이미지를 만들어주세요.",
                f"페이지 타입: {page['type']}",
            ]

            if page['type'] != 'COVER' and cover_color_palette:
                add_log(f"🎨 색상 팔레트 적용: {cover_color_palette}", indent=2)
                prompt_parts.append(f"**[색상 팔레트 통일]** 반드시 다음 색상 팔레트를 유지하세요: '{cover_color_palette}'")

            prompt_parts.extend([
                "**[필수 지시사항]**",
                "1. 텍스트는 반드시 한글이 깨지지 않게 크고 명확하게 배치해야 합니다.",
                "2. 모든 페이지는 일관된 톤앤매너를 유지합니다.",
                f"3. **이미지 비율은 반드시 '{ratio}'**여야 합니다.",
                f"4. 다음 내용을 포함하세요: {json.dumps(page['data'], ensure_ascii=False)}",
            ])

            # 참조 이미지 추가
            prompt_parts.extend(ref_images)
            add_log(f"📋 프롬프트 구성 완료 (텍스트 {len(prompt_parts)-len(ref_images)}개 + 이미지 {len(ref_images)}개)", indent=1)

            # 5. 이미지 생성 API 호출
            add_log(f"🤖 Google Gemini API 호출 시작...", indent=1)
            
            try:
                response = st.session_state.designer_model.generate_content(prompt_parts)
                add_log(f"✅ API 응답 수신 완료", indent=1)
            except Exception as api_err:
                add_log(f"❌ API 호출 실패: {api_err}", indent=1)
                raise

            if response and response.parts:
                generated_image = None
                for part in response.parts:
                    if hasattr(part, 'inline_data'):
                        generated_image = Image.open(io.BytesIO(part.inline_data.data))
                        break

                if generated_image:
                    add_log(f"✅ 이미지 생성 완료 (크기: {generated_image.size})", indent=1)
                    return generated_image, cover_color_palette
                else:
                    add_log(f"⚠️ 이미지 생성 실패 - 데이터 없음", indent=1)
                    return None, cover_color_palette
            else:
                add_log(f"❌ API 응답 오류", indent=1)
                return None, cover_color_palette

        except Exception as e:
            add_log(f"❌ 오류: {e}", indent=1)
            return None, cover_color_palette

# ==========================================
# 🔐 좌측 사이드바: 설정 및 갤러리
# ==========================================
with st.sidebar:
        st.title("⚙️ 설정 및 보관함")
        
        # 1. API 설정 섹션
        with st.expander("🔑 Google API 설정", expanded=not bool(st.session_state.google_api_key)):
                st.info("API Key가 필요합니다.")
                st.markdown("👉 [Google AI Studio에서 발급받기](https://aistudio.google.com/apikey)")
                
                api_key_input = st.text_input(
                        "API Key 입력",
                        type="password",
                        key="api_key_sidebar",
                        placeholder="AIzaSy..."
                )

                if api_key_input:
                        st.session_state.google_api_key = api_key_input
                        try:
                                genai.configure(api_key=api_key_input)
                                st.session_state.planner_model = genai.GenerativeModel('gemini-2.0-flash')
                                st.session_state.designer_model = genai.GenerativeModel('gemini-3-pro-image-preview')
                                st.success("✅ 연동 성공!")
                        except Exception as e:
                                st.error(f"연동 실패: {e}")
                                st.session_state.google_api_key = None
                else:
                        if not st.session_state.google_api_key:
                                st.warning("키를 입력해주세요.")

        st.divider()

        # 2. 글로벌 갤러리 섹션 (3열 썸네일 + 팝업)
        st.header("📂 갤러리")
        
        col_refresh, col_txt = st.columns([1, 2])
        with col_refresh:
                if st.button("🔄", help="새로고침"):
                        st.rerun()
        with col_txt:
                st.caption("outputs 폴더 자동 연동")

        gallery_files = load_global_gallery_images()

        if gallery_files:
                # 3개씩 묶어서 처리 (그리드 레이아웃)
                # 최근 60장까지만 표시 (성능 고려)
                recent_files = gallery_files[:60]
                
                # 3열 그리드 생성 logic
                for i in range(0, len(recent_files), 3):
                        # 3개씩 슬라이싱해서 한 줄(row)을 만듦
                        row_files = recent_files[i:i+3]
                        cols = st.columns(3)
                        
                        for j, file_path in enumerate(row_files):
                                with cols[j]:
                                        # 썸네일 이미지
                                        st.image(str(file_path), use_column_width=True)
                                        
                                        # 돋보기 버튼 (누르면 팝업)
                                        # key를 유니크하게 만들어야 에러가 안 남
                                        if st.button("🔍", key=f"zoom_{i}_{j}", help=file_path.name, use_container_width=True):
                                                show_image_modal(file_path)
                                                st.rerun()
                
                if len(gallery_files) > 60:
                        st.divider()
                        st.caption(f"외 {len(gallery_files) - 60}개의 이미지가 더 있습니다.")
                        
        else:
                st.info("📭 저장된 이미지가 없습니다.")

        # 앱 정보
        st.divider()
        st.caption(f"App v1.0 | Gemini Powered")

# ==========================================
# 📰 메인 헤더
# ==========================================
st.markdown("""
<div class="main-header">
        <h1>📰 광양시 AI 카드뉴스 생성기</h1>
        <p>기획부터 디자인까지 원클릭 자동화</p>
</div>
""", unsafe_allow_html=True)

# 확대된 이미지 표시 (사이드바에서 🔍 버튼 클릭 시)
if st.session_state.current_zoom_image and Path(st.session_state.current_zoom_image).exists():
        with st.expander("📸 이미지 크게 보기", expanded=True):
                st.image(st.session_state.current_zoom_image, use_column_width=True)
                
                # 다운로드 버튼
                with open(st.session_state.current_zoom_image, "rb") as f:
                        file_bytes = f.read()
                        st.download_button(
                                label="💾 원본 다운로드",
                                data=file_bytes,
                                file_name=Path(st.session_state.current_zoom_image).name,
                                mime="image/png",
                                key="zoom_download"
                        )
                
                # 닫기 버튼
                if st.button("❌ 닫기", key="close_zoom"):
                        st.session_state.current_zoom_image = None
                        st.rerun()

# API Key 검증
if not st.session_state.google_api_key:
        st.warning("⚠️ 좌측 사이드바에서 Google API Key를 입력해주세요.")
        st.stop()

# 인덱스 로드
if st.session_state.index_data is None:
        st.session_state.index_data = load_style_index()
        if st.session_state.index_data is None:
            st.error("❌ 스타일 인덱스를 로드할 수 없습니다.")
            st.info("gwangyang_style_db.jsonl 또는 gwangyang_style_index.pkl 파일이 필요합니다.")
            st.stop()

# ==========================================
# 📋 STEP 1: 기획안 생성
# ==========================================
st.markdown('<div class="step-header"><h2>STEP 1️⃣ 기획안 생성</h2></div>', unsafe_allow_html=True)

col_upload, col_detail = st.columns([2, 1])

with col_upload:
        uploaded_file = st.file_uploader(
            "📄 공고문 업로드 (TXT/PDF)",
            type=["txt", "pdf"],
            help="분석할 공고문 파일을 선택하세요"
        )

with col_detail:
        detail_level = st.radio(
            "📋 기획 상세도",
            ["간단하게 (1~2장)", "자세하게 (여러 장)"],
            horizontal=False
        )

if uploaded_file is not None:
        file_content = None
        query_text = ""

        try:
            if uploaded_file.type == "text/plain":
                file_content = uploaded_file.read().decode('utf-8')
                query_text = file_content[:500]
                add_log(f"📄 텍스트 파일 로드: {uploaded_file.name}")

            elif uploaded_file.type == "application/pdf":
                # PDF 처리 (텍스트 추출)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getbuffer())
                    tmp_path = tmp_file.name

                try:
                    add_log("📑 PDF 파일 감지됨")
                    add_log("📖 PDF 텍스트 추출 중...")

                    pdf_text = ""
                    try:
                        pdf_reader = PdfReader(tmp_path)
                        add_log(f"   총 {len(pdf_reader.pages)}페이지 검출")

                        for i in range(min(3, len(pdf_reader.pages))):
                            extracted = pdf_reader.pages[i].extract_text()
                            if extracted:
                                pdf_text += extracted + "\n"
                    except Exception as e:
                        add_log(f"⚠️ PDF 텍스트 추출 오류: {e}")
                        pdf_text = "[PDF 텍스트 추출 실패]"

                    if not pdf_text:
                        pdf_text = "[빈 PDF]"

                    add_log(f"✅ PDF 텍스트 추출 완료 ({len(pdf_text)}자)")
                    file_content = pdf_text
                    query_text = pdf_text[:1000]

                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            # 기획 버튼
            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("✨ AI 기획 시작", key="btn_planning", type="primary", use_container_width=True):
                    with st.spinner("🤔 기획 중..."):
                        try:
                            st.session_state.log_messages = []
                            add_log("=" * 60)
                            add_log("🚀 [STEP 1] 기획 프로세스 시작...")
                            add_log("=" * 60)

                            # RAG 검색
                            add_log("📚 유사 스타일 검색 중...")
                            examples = search_rag_references(
                                st.session_state.index_data,
                                query_text,
                                top_k=3
                            )

                            example_text = "\n".join([
                                json.dumps(
                                    {k: v for k, v in (ex.items() if isinstance(ex, dict) else [])
                                    if k in ['page_type', 'main_title', 'tone_and_manner']},
                                    ensure_ascii=False
                                )
                                for ex in examples
                            ]) if examples else ""

                            # 프롬프트 구성
                            if "간단" in detail_level:
                                structure_instr = "1. **구조 판단:** 내용을 최대한 압축하여 SINGLE(1장) 또는 간단한 MULTI로 제한하세요."
                                content_instr = "2. **내용 요약:** 매우 간단하고 임팩트 있게 요약하세요."
                            else:
                                structure_instr = "1. **구조 판단:** 내용이 단순하면 SINGLE, 복잡하면 MULTI 구조로 판단하세요."
                                content_instr = "2. **내용 요약:** 핵심 정보를 누락 없이 요약하세요."

                            prompt = [
                                "당신은 광양시청 홍보팀 수석 카드뉴스 기획자입니다.",
                                "제공된 공고문을 정밀하게 분석하세요.",
                                "\n[참고할 스타일 예시]",
                                example_text if example_text else "예시 없음",
                                "\n[분석할 공고문]",
                                file_content,
                                "\n[지시사항]",
                                structure_instr,
                                content_instr,
                                "3. **출력 형식:** 반드시 아래 JSON 형식으로만 출력하세요.",
                                """{
"structure_type": "MULTI",
"plan": {
        "cover": { "main_title": "...", "sub_title": "..." },
        "body": [ { "page": 1, "summary": ["..."] } ],
        "outro": { "contact": "..." }
},
"estimated_tone": "..."
}"""
                            ]

                            add_log("🧠 AI가 기획안을 작성 중입니다...")

                            max_retries = 3
                            response = None

                            for attempt in range(max_retries):
                                try:
                                    response = st.session_state.planner_model.generate_content(prompt)
                                    break
                                except Exception as e:
                                    add_log(f"⚠️ 시도 {attempt + 1}/{max_retries}: {e}")
                                    if attempt < max_retries - 1:
                                        time.sleep(2 ** attempt)

                            if response:
                                response_text = response.text.strip()
                                if response_text.startswith("```json"):
                                    response_text = response_text[7:]
                                if response_text.endswith("```"):
                                    response_text = response_text[:-3]

                                plan_data = json.loads(response_text)
                                st.session_state.plan_data = plan_data

                                add_log("\n" + "=" * 60)
                                add_log("🎉 [성공] 기획안이 완성되었습니다!")
                                add_log("=" * 60)

                                st.success("✅ 기획안 생성 완료!")

                        except Exception as e:
                            add_log(f"❌ 기획 오류: {e}")
                            st.error(f"❌ 오류 발생:\n{e}")

            with col_btn2:
                if st.button("🔄 로그 새로고침", key="btn_refresh_log", use_container_width=True):
                    st.rerun()

        except Exception as e:
            st.error(f"❌ 파일 처리 오류: {e}")

# 기획안 결과 표시
if st.session_state.plan_data is not None:
        st.divider()
        st.markdown("### 📝 기획안 결과")

        tab1, tab2 = st.tabs(["📖 보기", "✏️ 수정"])

        with tab1:
            plan_text = render_plan_text(st.session_state.plan_data)
            st.text(plan_text)

        with tab2:
            edit_plan_form()

# ==========================================
# 🎨 STEP 2: 디자인 생성
# ==========================================
if st.session_state.plan_data is not None:
        st.markdown('<div class="step-header"><h2>STEP 2️⃣ 디자인 생성</h2></div>', unsafe_allow_html=True)

        col_ratio, col_tone = st.columns([1, 2])

        with col_ratio:
            aspect_ratio = st.radio(
                "📐 비율 선택",
                ["4:5 (인스타그램)", "1:1 (정방형)", "9:16 (릴스/스토리)"],
                horizontal=False
            )

        with col_tone:
            tone = st.session_state.plan_data.get('estimated_tone', '미지정')
            st.info(f"📌 **예상 톤**: {tone}")

        # 처음 설정할 때만 페이지 구성
        if st.session_state.design_pages is None:
            if st.button("➡️ 다음", key="btn_design_start", type="primary", use_container_width=True):
                # 👇 [추가] 새로운 디자인 시작시 공유 레퍼런스 초기화
                st.session_state.shared_body_refs = None
                
                # 페이지 구성
                tone = st.session_state.plan_data.get("estimated_tone", "광양시 스타일")
                plan = st.session_state.plan_data["plan"]
                ratio = aspect_ratio.split()[0]  # "4:5", "1:1", "9:16"

                pages = []
                if "cover" in plan:
                    pages.append({
                        "type": "COVER",
                        "data": plan["cover"],
                        "order": 0
                    })

                if "body" in plan:
                    for i, page_data in enumerate(plan["body"]):
                        pages.append({
                            "type": "BODY",
                            "data": page_data,
                            "order": i + 1
                        })

                if "outro" in plan:
                    pages.append({
                        "type": "OUTRO",
                        "data": plan["outro"],
                        "order": len(pages)
                    })

                st.session_state.design_pages = pages
                st.session_state.design_aspect_ratio = ratio
                st.session_state.log_messages = []
                add_log("=" * 60)
                add_log("🚀 [STEP 2] 디자인 프로세스 시작...")
                add_log("=" * 60)
                add_log(f"🎨 총 {len(pages)}장의 이미지를 생성합니다. (비율 {ratio})")
                st.rerun()

        # 시작 페이지 선택 및 생성
        if st.session_state.design_pages is not None and len(st.session_state.generated_design_images) == 0 and st.session_state.current_page_idx == 0:
            st.markdown("---")
            st.markdown("#### 📍 시작 페이지 선택")

            col_select, col_btn = st.columns([2, 1])

            with col_select:
                start_page = st.selectbox(
                    "몇 페이지부터 생성할까요?",
                    options=list(range(1, len(st.session_state.design_pages) + 1)),
                    index=0,
                    key="start_page_select"
                )

            with col_btn:
                st.write("")  # 공간 맞추기
                if st.button("🚀 선택 및 생성 시작", key="btn_start_generate", type="primary", use_container_width=True):
                    st.session_state.current_page_idx = start_page  # 1부터 시작 (0이 아님)
                    st.session_state.generation_result = None
                    st.rerun()

        # 🟢 [블록 1] 생성 로직 (결과가 없을 때만 실행)
        if st.session_state.design_pages is not None and st.session_state.current_page_idx > 0 and st.session_state.generation_result is None:
            tone = st.session_state.plan_data.get("estimated_tone", "광양시 스타일")
            ratio = st.session_state.design_aspect_ratio
            pages = st.session_state.design_pages
            current_idx = st.session_state.current_page_idx - 1  # 배열 인덱스로 변환

            # 이전에 생성된 이미지들 표시
            if len(st.session_state.generated_design_images) > 0:
                st.markdown("---")
                st.markdown("#### 📸 지금까지 생성된 페이지")

                for gen_img in st.session_state.generated_design_images:
                    col_img, col_down = st.columns([3, 1])

                    with col_img:
                        # 여기도 width=450 으로 수정
                        st.image(gen_img["image"], caption=f"{gen_img['type']} - 페이지 {gen_img['order']}", width=450)

                    with col_down:
                        st.download_button(
                            label="📥 다운로드",
                            data=get_image_download_data(gen_img["image"]),
                            file_name=f"card_news_{gen_img['type'].lower()}_{gen_img['order']}.png",
                            mime="image/png",
                            key=f"download_progress_{gen_img['order']}"
                        )

                # 다음 페이지 생성 여부 확인
            if current_idx < len(pages):
                st.markdown("---")
                st.markdown(f"#### 🎨 페이지 {current_idx + 1}/{len(pages)} 생성 중")

                # 진행상황 표시
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.container()

                status_text.text(f"⏳ 페이지 {current_idx + 1}/{len(pages)} 생성 준비 중...")

                # 생성 결과가 아직 없으면 실제 생성 수행
                if st.session_state.generation_result is None:
                    try:
                        cover_color_palette = None
                        # COVER 페이지가 이미 생성됐으면 색상팔레트 유지
                        if current_idx > 0 and len(st.session_state.generated_design_images) > 0:
                            # 이전에 저장된 색상팔레트 사용
                            first_image = st.session_state.generated_design_images[0]
                            cover_color_palette = first_image.get('palette', None)

                        # 현재 페이지 생성
                        status_text.text(f"🤔 페이지 {current_idx + 1}/{len(pages)} 생성 중... (1~5분 소요)")
                        progress_bar.progress((current_idx) / len(pages))

                        generated_image, cover_color_palette = generate_single_page_design(
                            current_idx, pages, tone, ratio, cover_color_palette
                        )

                        # 생성 결과 저장
                        st.session_state.generation_result = {
                            'image': generated_image,
                            'palette': cover_color_palette,
                            'error': None
                        }

                    except Exception as e:
                        add_log(f"❌ 페이지 생성 오류: {e}")
                        st.session_state.generation_result = {
                            'image': None,
                            'palette': None,
                            'error': str(e)
                        }
                    finally:
                        pass

        # 🟢 [블록 2] UI 표시 로직 (결과가 있으면 무조건 실행 - 들여쓰기가 밖으로!)
        if st.session_state.design_pages is not None and st.session_state.current_page_idx > 0 and st.session_state.generation_result is not None:

            # 필요한 변수 재할당
            pages = st.session_state.design_pages
            current_idx = st.session_state.current_page_idx - 1

            generated_image = st.session_state.generation_result['image']
            error = st.session_state.generation_result['error']
            cover_color_palette = st.session_state.generation_result['palette']

            # 로그 표시
            with st.expander("📋 상세 생성 로그 보기", expanded=False):
                log_text = "\n".join(st.session_state.log_messages)
                st.code(log_text, language="text")

            if generated_image:
                # 이미지를 리스트에 추가 (중복 체크)
                already_added = any(
                    img.get('order') == pages[current_idx]['order']
                    for img in st.session_state.generated_design_images
                )

                if not already_added:
                    # 1. 로컬 폴더에 파일 저장
                    save_path = None
                    try:
                        file_name = f"card_news_{pages[current_idx]['type'].lower()}_{pages[current_idx]['order']}.png"
                        save_path = st.session_state.output_dir / file_name
                        generated_image.save(save_path)
                        add_log(f"💾 파일 저장됨: {save_path}")
                    except Exception as e:
                        add_log(f"⚠️ 파일 저장 실패: {e}")

                    # 2. 세션 상태에 저장
                    st.session_state.generated_design_images.append({
                        "image": generated_image,
                        "type": pages[current_idx]['type'],
                        "order": pages[current_idx]['order'],
                        "path": str(save_path) if save_path else None  # 경로도 같이 저장
                    })
                    add_log(f"✅ 페이지 {current_idx + 1} 생성 및 리스트 등록 완료!")

                # 생성된 이미지 표시
                st.divider()
                st.markdown(f"#### 🎨 생성된 페이지 ({pages[current_idx]['type']} - 페이지 {current_idx + 1})")
                col_img, col_down = st.columns([3, 1])

                with col_img:
                    # width=450 으로 고정해서 한눈에 들어오게 수정
                    st.image(generated_image, width=450)

                with col_down:
                    st.download_button(
                        label="📥 다운로드",
                        data=get_image_download_data(generated_image),
                        file_name=f"card_news_{pages[current_idx]['type'].lower()}_{current_idx + 1}.png",
                        mime="image/png",
                        key=f"download_current_{current_idx}"
                    )

                # 다음 페이지 네비게이션
                if current_idx + 1 < len(pages):
                    st.divider()
                    st.markdown("#### ❓ 다음 어떻게 하시겠어요?")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("➡️ 다음 페이지만", key=f"btn_next_page_{current_idx}", use_container_width=True):
                            st.session_state.current_page_idx += 1
                            st.session_state.generation_result = None
                            st.rerun()

                    with col2:
                        if st.button("⏭️ 모두 생성하기", key=f"btn_generate_all_{current_idx}", use_container_width=True):
                            st.session_state.current_page_idx += 1
                            st.session_state.auto_generate_all = True
                            st.session_state.generation_result = None
                            st.rerun()

                    with col3:
                        if st.button("⏹️ 중단하기", key=f"btn_stop_{current_idx}", use_container_width=True):
                            st.session_state.current_page_idx = 0
                            st.session_state.generation_result = None
                            st.rerun()
                else:
                    st.divider()
                    st.success("🎉 모든 페이지 생성이 완료되었습니다!")
                    if st.button("🔄 처음부터 다시", key="btn_restart"):
                        st.session_state.current_page_idx = 0
                        st.session_state.generated_design_images = []
                        st.session_state.generation_result = None
                        st.session_state.auto_generate_all = False
                        st.rerun()
            else:
                # 에러 처리
                st.error(f"❌ 페이지 {current_idx + 1} 생성 실패")
                if error:
                    st.error(f"**오류 상세**: {error}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 재시도", key=f"btn_retry_{current_idx}", type="primary", use_container_width=True):
                        st.session_state.generation_result = None
                        st.rerun()
                with col2:
                    if st.button("⏹️ 중단", key=f"btn_stop_error_{current_idx}", use_container_width=True):
                        st.session_state.current_page_idx = 0
                        st.session_state.generation_result = None
                        st.rerun()

        # 자동 생성 모드 처리
        if "auto_generate_all" in st.session_state and st.session_state.auto_generate_all:
            if st.session_state.generation_result is not None and st.session_state.generation_result.get('image') is not None:
                time.sleep(1)
                if st.session_state.current_page_idx < len(st.session_state.design_pages):
                    st.session_state.current_page_idx += 1
                    st.session_state.generation_result = None
                    st.rerun()
                else:
                    st.session_state.auto_generate_all = False
                    st.rerun()

# ==========================================
# 📋 통합 로그 뷰 (페이지 하단)
# ==========================================
if st.session_state.log_messages:
        st.divider()
        st.markdown("### 📋 실행 로그")
        display_logs()
