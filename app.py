import streamlit as st
from gtts import gTTS
import io
import re
import json
import os
import unicodedata

# 앱 기본 설정
st.set_page_config(page_title="스페인어 받아쓰기 연습장", page_icon="🇪🇸", layout="wide")

# 모바일에서도 무조건 한 줄(가로) 정렬을 유지하는 CSS 강제 적용
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        h1 { font-size: 1.3rem !important; margin-bottom: 0.1rem !important; }
        h3 { font-size: 1.0rem !important; margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }
        
        /* 모바일 화면에서도 3개 버튼을 무조건 1행에 배치하는 강제 CSS */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0.3rem !important;
        }
        
        div[data-testid="column"] {
            flex: 1 1 auto !important;
            min-width: 0px !important;
            width: auto !important;
        }
        
        /* 버튼 높이, 글자 크기, 여백 최적화 */
        div[data-testid="stButton"] > button {
            padding: 0.2rem 0.1rem !important;
            font-size: 0.75rem !important;
            min-height: 2.2rem !important;
            white-space: nowrap !important;
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🇪🇸 나만의 스페인어 Daily Dictation")

JSON_FILENAME = "dele_spanish.json"

# --- [1] 기본 데이터 및 JSON 자동 로드 ---
DEFAULT_TOPICS = {
    "🌱 [B1] 일상의 변화 (Sample)": [
        {"es": "Últimamente he sentido que necesito cambiar mi estilo de vida.", "ko": "최근에 내 라이프스타일을 바꿀 필요가 있다고 느꼈어."},
        {"es": "Por eso, he empezado a hacer ejercicio todas las mañanas.", "ko": "그래서 매일 아침 운동을 하기 시작했지."},
        {"es": "Al principio fue muy difícil levantarme temprano, pero ahora me siento lleno de energía.", "ko": "처음에는 일찍 일어나는 게 너무 힘들었지만, 지금은 에너지가 넘쳐."}
    ]
}

def load_json_files_from_repo():
    repo_topics = {}
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            for title, story in data.items():
                                repo_topics[title] = story
                except Exception:
                    pass
    return repo_topics

def save_to_dele_json(title, story):
    """ dele_spanish.json 파일에 새 데이터 누적 저장 """
    data = {}
    if os.path.exists(JSON_FILENAME):
        try:
            with open(JSON_FILENAME, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    
    data[title] = story
    
    with open(JSON_FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 세션 상태 관리
if 'topics' not in st.session_state:
    loaded_topics = DEFAULT_TOPICS.copy()
    loaded_topics.update(load_json_files_from_repo())
    st.session_state.topics = loaded_topics

if 'selected_topic' not in st.session_state or st.session_state.selected_topic not in st.session_state.topics:
    st.session_state.selected_topic = list(st.session_state.topics.keys())[0]

if 'index' not in st.session_state:
    st.session_state.index = 0

if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

# --- [2] 사이드바 ---
st.sidebar.header("📚 학습 주제 선택")
topic_names = list(st.session_state.topics.keys())

try:
    current_nav_index = topic_names.index(st.session_state.selected_topic)
except ValueError:
    current_nav_index = 0

selected_nav = st.sidebar.selectbox("연습할 주제를 고르세요:", topic_names, index=current_nav_index)

if selected_nav != st.session_state.selected_topic:
    st.session_state.selected_topic = selected_nav
    st.session_state.index = 0
    st.session_state.show_answer = False
    st.session_state.user_input = ""
    st.rerun()

st.sidebar.divider()
st.sidebar.header("➕ 새 콘텐츠 추가하기")
tab_ai, tab1, tab2 = st.sidebar.tabs(["🤖 AI 텍스트 복붙", "✍️ 직접 작성", "📁 JSON 업로드"])

# --- [신규 기능 1] AI 텍스트 복붙 기능 ---
with tab_ai:
    st.caption("ChatGPT나 Claude가 출력한 문장을 붙여넣으면 `dele_spanish.json`에 바로 저장됩니다.")
    
    with st.expander("💡 AI 프롬프트 예시 보기"):
        st.code("""스페인어 B2 수준 문장 3개를 만들어줘.
형식:
[스페인어 문장]
[한국어 번역]""", language="text")

    with st.form("add_ai_text_form"):
        ai_title = st.text_input("주제/레슨 제목", placeholder="예: [B2] 환경 문제와 미래")
        ai_raw_text = st.text_area(
            "AI 생성 텍스트 붙여넣기", 
            height=150, 
            placeholder="1. 스페인어 문장\n한국어 번역\n\n2. 스페인어 문장\n한국어 번역\n\n또는\n스페인어 문장 | 한국어 번역"
        )
        ai_submit_btn = st.form_submit_button("`dele_spanish.json`에 저장하기")

        if ai_submit_btn:
            if not ai_title or not ai_raw_text:
                st.error("제목과 텍스트 내용을 모두 입력해 주세요.")
            else:
                lines = [line.strip() for line in ai_raw_text.strip().split('\n') if line.strip()]
                parsed_story = []

                # 구문 분석 1: '스페인어 | 한국어' 형식인 경우
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        es_p = re.sub(r'^\d+[\.\)]\s*', '', parts[0].strip())
                        ko_p = parts[1].strip()
                        parsed_story.append({"es": es_p, "ko": ko_p})

                # 구문 분석 2: 줄바꿈으로 스페인어-한국어 번갈아 나오는 경우
                if not parsed_story:
                    i = 0
                    while i < len(lines):
                        es_line = re.sub(r'^\d+[\.\)]\s*', '', lines[i].strip())
                        ko_line = lines[i+1].strip() if (i + 1) < len(lines) else "번역 없음"
                        parsed_story.append({"es": es_line, "ko": ko_line})
                        i += 2

                if parsed_story:
                    # 1. 파일에 저장
                    save_to_dele_json(ai_title, parsed_story)
                    
                    # 2. 세션 상태 업데이트 및 이동
                    st.session_state.topics[ai_title] = parsed_story
                    st.session_state.selected_topic = ai_title
                    st.session_state.index = 0
                    st.session_state.show_answer = False
                    st.session_state.user_input = ""
                    st.sidebar.success(f"'{ai_title}' 레슨이 dele_spanish.json 에 저장되었습니다!")
                    st.rerun()
                else:
                    st.error("텍스트를 분석하지 못했습니다. 형식을 확인해 주세요.")

with tab1:
    with st.form("add_text_form"):
        new_title = st.text_input("주제/레슨 제목", placeholder="예: [B2] 뉴스와 환경")
        es_raw = st.text_area("스페인어 지문 (줄단위)", height=100)
        ko_raw = st.text_area("한국어 번역 (줄단위)", height=100)
        submit_btn = st.form_submit_button("레슨 등록하기")
        
        if submit_btn:
            if not new_title or not es_raw or not ko_raw:
                st.error("모든 항목을 입력해 주세요!")
            else:
                es_lines = [line.strip() for line in es_raw.strip().split('\n') if line.strip()]
                ko_lines = [line.strip() for line in ko_raw.strip().split('\n') if line.strip()]
                
                if len(es_lines) != len(ko_lines):
                    st.error(f"스페인어({len(es_lines)}줄)와 한국어({len(ko_lines)}줄)의 줄 수가 다릅니다.")
                else:
                    new_story = [{"es": es, "ko": ko} for es, ko in zip(es_lines, ko_lines)]
                    
                    # 파일 및 세션 저장
                    save_to_dele_json(new_title, new_story)
                    st.session_state.topics[new_title] = new_story
                    st.session_state.selected_topic = new_title
                    st.session_state.index = 0
                    st.session_state.show_answer = False
                    st.session_state.user_input = ""
                    st.success("등록 완료 및 json 파일 저장이 완료되었습니다!")
                    st.rerun()

with tab2:
    st.caption("JSON 양식 파일(.json)을 올리면 문제집이 생성됩니다.")
    uploaded_file = st.sidebar.file_uploader("JSON 파일 선택", type=["json"], key="json_uploader")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            first_added_title = None
            for title, story in data.items():
                if title not in st.session_state.topics:
                    st.session_state.topics[title] = story
                    save_to_dele_json(title, story)
                    if first_added_title is None:
                        first_added_title = title
            
            if first_added_title:
                st.session_state.selected_topic = first_added_title
                st.session_state.index = 0
                st.session_state.show_answer = False
                st.session_state.user_input = ""
                st.sidebar.success("성공적으로 불러왔습니다!")
                st.rerun()
        except Exception:
            st.sidebar.error("JSON 파싱 에러! 파일 형식을 확인하세요.")

# --- [3] 유틸리티 함수 ---
def clean_text(text):
    text = text.lower()
    text = text.replace('ñ', '___N_TILDE___')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = unicodedata.normalize('NFC', text)
    text = text.replace('___N_TILDE___', 'ñ')
    text = re.sub(r'[^a-z0-9\sñ]', '', text)
    return text.strip()

def get_highlighted_user_text(user_text, correct_text):
    user_words = user_text.split()
    correct_clean_words = clean_text(correct_text).split()
    
    highlighted = []
    for i, word in enumerate(user_words):
        clean_w = clean_text(word)
        correct_w = correct_clean_words[i] if i < len(correct_clean_words) else ""
        
        if clean_w == correct_w:
            highlighted.append(word)
        else:
            highlighted.append(f"<span style='background-color: #ffcdd2; color: #b71c1c; padding: 1px 4px; border-radius: 3px; font-weight: bold;'>{word}</span>")
            
    return " ".join(highlighted)

@st.cache_data
def get_audio(text, speed=False):
    tts = gTTS(text=text, lang='es', slow=speed)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp.getvalue()

# --- [4] 메인 학습 화면 ---
current_story = st.session_state.topics[st.session_state.selected_topic]

if st.session_state.index >= len(current_story):
    st.session_state.index = 0

current_item = current_story[st.session_state.index]

# 타이틀 및 진행도
st.markdown(f"### 📌 {st.session_state.selected_topic} ({st.session_state.index + 1} / {len(current_story)})")

# 오디오 재생 플레이어
st.audio(get_audio(current_item['es'], speed=False), format='audio/mp3', autoplay=True)

# 폼(Form) 구조를 이용해 엔터 키 제출 처리
with st.form(key=f"dict_form_{st.session_state.selected_topic}_{st.session_state.index}", clear_on_submit=False):
    user_input = st.text_area(
        "스페인어로 받아 적으세요:", 
        value=st.session_state.user_input,
        height=100,
        key=f"input_field_{st.session_state.selected_topic}_{st.session_state.index}",
        placeholder="여기에 스페인어 문장을 입력하세요..."
    )
    
    # [수정 2 반영] 3개 컬럼을 완전히 동일한 가로 비율(1:1:1)로 설정
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        prev_btn = st.form_submit_button("⬅️ 이전", use_container_width=True)

    with btn_col2:
        next_btn = st.form_submit_button("다음 ➡️", use_container_width=True)

    with btn_col3:
        check_btn = st.form_submit_button("🔎 정답확인", use_container_width=True, type="primary")

# 버튼 이벤트 동작
if check_btn:
    st.session_state.user_input = user_input
    st.session_state.show_answer = True
    st.rerun()

elif prev_btn:
    if st.session_state.index > 0:
        st.session_state.index -= 1
        st.session_state.show_answer = False
        st.session_state.user_input = ""
        st.rerun()

elif next_btn:
    if st.session_state.index < len(current_story) - 1:
        st.session_state.index += 1
        st.session_state.show_answer = False
        st.session_state.user_input = ""
        st.rerun()
    else:
        st.success("🎉 레슨의 마지막 문장입니다!")

# --- [5] 채점 결과 표시 ---
if st.session_state.show_answer:
    user_clean = clean_text(st.session_state.user_input)
    answer_clean = clean_text(current_item['es'])
    
    if user_clean == answer_clean:
        st.success("🎉 **정답입니다! Perfect!**")
    else:
        st.error("❌ **틀린 단어를 확인해보세요.**")
    
    if st.session_state.user_input.strip():
        highlighted_user_text = get_highlighted_user_text(st.session_state.user_input, current_item['es'])
        st.markdown(f"✍️ **내 답:** {highlighted_user_text}", unsafe_allow_html=True)
    else:
        st.markdown("✍️ **내 답:** *(입력값 없음)*")

    st.markdown(f"👉 **정답:** `{current_item['es']}`")
    st.info(f"💡 **뜻:** {current_item['ko']}")