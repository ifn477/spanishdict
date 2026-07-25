import streamlit as st
from gtts import gTTS
import io
import re
import json
import os
import unicodedata

# 앱 기본 설정
st.set_page_config(page_title="스페인어 받아쓰기 연습장", page_icon="🇪🇸", layout="wide")

# JSON 저장 파일 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILENAME = os.path.join(BASE_DIR, "dele_spanish.json")

# ----------------------------------------------------
# [강력 수정] 상단 여백 확보 및 모바일 버튼 강제 가로 3등분
# ----------------------------------------------------
st.markdown("""
    <style>
        /* 1. 상단 메뉴바 가림 방지 여백 확보 */
        .main .block-container {
            padding-top: 4.5rem !important;
            padding-bottom: 2rem !important;
        }
        
        h1 { 
            font-size: 1.2rem !important; 
            margin-top: 0rem !important;
            margin-bottom: 0.5rem !important;
        }
        h3 { font-size: 0.95rem !important; }

        /* 2. Form 내 가로 블록 강제 1행 유지 */
        form div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            gap: 4px !important;
        }

        /* 3. 컬럼 각각을 정확히 가로 33.33%로 강제 */
        form div[data-testid="stColumn"], 
        form div[data-testid="column"] {
            width: 33.33% !important;
            min-width: 0px !important;
            flex: 1 1 33.33% !important;
        }

        /* 4. 버튼 상자가 화면을 벗어나거나 거대해지지 않도록 가로 1/3 고정 */
        form div[data-testid="stButton"] {
            width: 100% !important;
        }

        form div[data-testid="stButton"] > button {
            width: 100% !important;
            min-width: 0px !important;
            padding: 0px 2px !important;
            font-size: 0.75rem !important;
            height: 2.2rem !important;
            min-height: 2.2rem !important;
            line-height: 2.2rem !important;
            white-space: nowrap !important;
        }
        
        form div[data-testid="stButton"] > button p {
            font-size: 0.75rem !important;
            white-space: nowrap !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🇪🇸 나만의 스페인어 Daily Dictation")

# --- [1] 데이터 로드 및 저장 함수 ---
DEFAULT_TOPICS = {
    "🌱 [B1] 일상의 변화 (Sample)": [
        {"es": "Últimamente he sentido que necesito cambiar mi estilo de vida.", "ko": "최근에 내 라이프스타일을 바꿀 필요가 있다고 느꼈어."},
        {"es": "Por eso, he empezado a hacer ejercicio todas las mañanas.", "ko": "그래서 매일 아침 운동을 하기 시작했지."},
        {"es": "Al principio fue muy difícil levantarme temprano, pero ahora me siento lleno de energía.", "ko": "처음에는 일찍 일어나는 게 너무 힘들었지만, 지금은 에너지가 넘쳐."}
    ]
}

def load_all_topics():
    topics = DEFAULT_TOPICS.copy()
    if os.path.exists(JSON_FILENAME):
        try:
            with open(JSON_FILENAME, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    topics.update(data)
        except Exception:
            pass
    return topics

def save_to_json_file(title, story):
    data = {}
    if os.path.exists(JSON_FILENAME):
        try:
            with open(JSON_FILENAME, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    
    data[title] = story
    try:
        with open(JSON_FILENAME, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# 세션 상태 관리
if 'topics' not in st.session_state:
    st.session_state.topics = load_all_topics()

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
tab_ai, tab1 = st.sidebar.tabs(["🤖 AI 텍스트 복붙", "✍️ 직접 작성"])

# AI 텍스트 복붙 기능
with tab_ai:
    st.caption("AI 문장을 붙여넣으면 `dele_spanish.json`에 저장이 됩니다.")
    
    with st.form("add_ai_text_form"):
        ai_title = st.text_input("주제/레슨 제목", placeholder="예: [B2] 환경 문제")
        ai_raw_text = st.text_area(
            "AI 텍스트 붙여넣기", 
            height=150, 
            placeholder="1. 스페인어 문장\n한국어 번역\n\n2. 스페인어 문장\n한국어 번역"
        )
        ai_submit_btn = st.form_submit_button("`dele_spanish.json`에 저장하기")

        if ai_submit_btn:
            if not ai_title or not ai_raw_text:
                st.error("제목과 내용을 입력하세요!")
            else:
                lines = [line.strip() for line in ai_raw_text.strip().split('\n') if line.strip()]
                parsed_story = []

                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        es_p = re.sub(r'^\d+[\.\)]\s*', '', parts[0].strip())
                        ko_p = parts[1].strip()
                        parsed_story.append({"es": es_p, "ko": ko_p})

                if not parsed_story:
                    i = 0
                    while i < len(lines):
                        es_line = re.sub(r'^\d+[\.\)]\s*', '', lines[i].strip())
                        ko_line = lines[i+1].strip() if (i + 1) < len(lines) else "번역 없음"
                        parsed_story.append({"es": es_line, "ko": ko_line})
                        i += 2

                if parsed_story:
                    if save_to_json_file(ai_title, parsed_story):
                        st.session_state.topics[ai_title] = parsed_story
                        st.session_state.selected_topic = ai_title
                        st.session_state.index = 0
                        st.session_state.show_answer = False
                        st.session_state.user_input = ""
                        st.sidebar.success("🎉 JSON 저장 성공!")
                        st.rerun()
                else:
                    st.error("형식을 확인해 주세요.")

with tab1:
    with st.form("add_text_form"):
        new_title = st.text_input("주제/레슨 제목")
        es_raw = st.text_area("스페인어 문장 (줄단위)")
        ko_raw = st.text_area("한국어 번역 (줄단위)")
        submit_btn = st.form_submit_button("등록 및 저장")
        
        if submit_btn:
            es_lines = [l.strip() for l in es_raw.split('\n') if l.strip()]
            ko_lines = [l.strip() for l in ko_raw.split('\n') if l.strip()]
            if len(es_lines) == len(ko_lines) and new_title:
                new_story = [{"es": es, "ko": ko} for es, ko in zip(es_lines, ko_lines)]
                save_to_json_file(new_title, new_story)
                st.session_state.topics[new_title] = new_story
                st.session_state.selected_topic = new_title
                st.session_state.index = 0
                st.session_state.show_answer = False
                st.session_state.user_input = ""
                st.rerun()

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
            highlighted.append(f"<span style='background-color: #ffcdd2; color: #b71c1c; padding: 1px 4px; border-radius: 3px;'>{word}</span>")
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

st.markdown(f"### 📌 {st.session_state.selected_topic} ({st.session_state.index + 1} / {len(current_story)})")
st.audio(get_audio(current_item['es']), format='audio/mp3', autoplay=True)

with st.form(key=f"dict_form_{st.session_state.selected_topic}_{st.session_state.index}", clear_on_submit=False):
    user_input = st.text_area(
        "스페인어로 받아 적으세요:", 
        value=st.session_state.user_input,
        height=100,
        placeholder="여기에 입력하세요..."
    )
    
    # 3개 컬럼 생성
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        prev_btn = st.form_submit_button("⬅️ 이전", use_container_width=True)
    with btn_col2:
        next_btn = st.form_submit_button("다음 ➡️", use_container_width=True)
    with btn_col3:
        check_btn = st.form_submit_button("🔎 정답", use_container_width=True, type="primary")

# 버튼 동작
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

# 채점
if st.session_state.show_answer:
    if clean_text(st.session_state.user_input) == clean_text(current_item['es']):
        st.success("🎉 **정답입니다!**")
    else:
        st.error("❌ **틀린 단어를 확인해보세요.**")
    
    if st.session_state.user_input.strip():
        st.markdown(f"✍️ **내 답:** {get_highlighted_user_text(st.session_state.user_input, current_item['es'])}", unsafe_allow_html=True)
    st.markdown(f"👉 **정답:** `{current_item['es']}`")
    st.info(f"💡 **뜻:** {current_item['ko']}")