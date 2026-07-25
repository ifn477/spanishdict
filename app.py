import streamlit as st
from gtts import gTTS
import io
import re
import json
import os
import unicodedata

# 앱 기본 설정
st.set_page_config(page_title="스페인어 받아쓰기 연습장", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 나만의 스페인어 Daily Dictation")

# --- [1] 기본 샘플 데이터 세팅 및 깃허브 내 JSON 파일 자동 로드 ---
DEFAULT_TOPICS = {
    "🌱 [B1] 일상의 변화 (Sample)": [
        {"es": "Últimamente he sentido que necesito cambiar mi estilo de vida.", "ko": "최근에 내 라이프스타일을 바꿀 필요가 있다고 느꼈어."},
        {"es": "Por eso, he empezado a hacer ejercicio todas las mañanas.", "ko": "그래서 매일 아침 운동을 하기 시작했지."},
        {"es": "Al principio fue muy difícil levantarme temprano, pero ahora me siento lleno de energía.", "ko": "처음에는 일찍 일어나는 게 너무 힘들었지만, 지금은 에너지가 넘쳐."}
    ]
}

# 깃허브 저장소에 올라간 모든 .json 파일을 읽어오는 함수
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

# --- [2] 사이드바: 주제 선택 및 파일 업로드 ---
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

tab1, tab2 = st.sidebar.tabs(["✍️ 직접 붙여넣기", "📁 JSON 파일 업로드"])

with tab1:
    with st.form("add_text_form"):
        new_title = st.text_input("주제/레슨 제목", placeholder="예: [B2] 뉴스와 환경")
        es_raw = st.text_area("스페인어 지문 (줄단위)", height=120)
        ko_raw = st.text_area("한국어 번역 (줄단위)", height=120)
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
                    st.session_state.topics[new_title] = new_story
                    st.session_state.selected_topic = new_title
                    st.session_state.index = 0
                    st.session_state.show_answer = False
                    st.session_state.user_input = ""
                    st.success("새 레슨이 성공적으로 등록되었습니다!")
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
                    if first_added_title is None:
                        first_added_title = title
            
            if first_added_title:
                st.session_state.selected_topic = first_added_title
                st.session_state.index = 0
                st.session_state.show_answer = False
                st.session_state.user_input = ""
                st.sidebar.success("성공적으로 불러왔습니다!")
                st.rerun()
                
        except Exception as e:
            st.sidebar.error("JSON 파싱 에러! 파일 형식을 확인하세요.")

# --- [3] 유틸리티 및 텍스트 정제 함수 ---
def clean_text(text):
    """
    1) 소문자화
    2) ñ을 제외한 모음 악센트(tilde) 제거 (á->a, é->e 등)
    3) 모든 문장부호 및 특수문자 제거
    """
    text = text.lower()
    # ñ을 임시 토큰으로 보존
    text = text.replace('ñ', '___N_TILDE___')
    # NFD 분해로 일반 모음 악센트 분리 및 제거
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = unicodedata.normalize('NFC', text)
    # ñ 복원
    text = text.replace('___N_TILDE___', 'ñ')
    # 알파벳, 숫자, 공백, ñ 이외 제거
    text = re.sub(r'[^a-z0-9\sñ]', '', text)
    return text.strip()

def get_highlighted_user_text(user_text, correct_text):
    """
    사용자가 입력한 문장에서 틀린 단어를 빨간색으로 강조 표시해 줍니다.
    """
    user_words = user_text.split()
    correct_clean_words = clean_text(correct_text).split()
    
    highlighted = []
    for i, word in enumerate(user_words):
        clean_w = clean_text(word)
        # 위치상의 정답 단어와 비교
        correct_w = correct_clean_words[i] if i < len(correct_clean_words) else ""
        
        if clean_w == correct_w:
            highlighted.append(word)
        else:
            # 틀린 단어는 빨간 배경으로 표시
            highlighted.append(f"<span style='background-color: #ffcdd2; color: #b71c1c; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>{word}</span>")
            
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

st.subheader(f"📌 {st.session_state.selected_topic}")
st.write(f"**문장 {st.session_state.index + 1} / {len(current_story)}**")

# 오디오 재생
col1, col2 = st.columns(2)
with col1:
    st.write("🔊 **정속 재생**")
    st.audio(get_audio(current_item['es'], speed=False), format='audio/mp3', autoplay=True)
with col2:
    st.write("🐢 **느리게 재생**")
    st.audio(get_audio(current_item['es'], speed=True), format='audio/mp3')

# 입력창
user_input = st.text_input(
    "스페인어로 받아 적으세요 (악센트 및 문장부호 생략 가능):", 
    value=st.session_state.user_input,
    key=f"input_field_{st.session_state.selected_topic}_{st.session_state.index}"
)

# 버튼 영역 (정답 확인 / 이전 문장 / 다음 문장)
btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])

with btn_col1:
    if st.button("🔎 정답 확인", use_container_width=True, type="primary"):
        st.session_state.user_input = user_input
        st.session_state.show_answer = True

with btn_col2:
    if st.button("⬅️ 이전 문장", use_container_width=True):
        if st.session_state.index > 0:
            st.session_state.index -= 1
            st.session_state.show_answer = False
            st.session_state.user_input = ""
            st.rerun()

with btn_col3:
    if st.button("다음 문장 ➡️", use_container_width=True):
        if st.session_state.index < len(current_story) - 1:
            st.session_state.index += 1
            st.session_state.show_answer = False
            st.session_state.user_input = ""
            st.rerun()
        else:
            st.success("🎉 이 레슨의 마지막 문장입니다!")

# --- [5] 정답 채점 및 오답노트 결과 표시 ---
if st.session_state.show_answer:
    st.divider()
    
    user_clean = clean_text(st.session_state.user_input)
    answer_clean = clean_text(current_item['es'])
    
    if user_clean == answer_clean:
        st.success("🎉 **정답입니다! Perfect!**")
    else:
        st.error("❌ **아쉽네요! 아래 틀린 부분을 확인하고 다시 시도해보세요.**")
    
    # 내가 작성한 답안 (틀린 단어 빨간색 하이라이트)
    if st.session_state.user_input.strip():
        highlighted_user_text = get_highlighted_user_text(st.session_state.user_input, current_item['es'])
        st.markdown(f"✍️ **내가 입력한 답:** {highlighted_user_text}", unsafe_allow_html=True)
    else:
        st.markdown("✍️ **내가 입력한 답:** *(입력값 없음)*")

    # 원문 정답 및 한국어 해석
    st.markdown(f"👉 **원문 정답:** `{current_item['es']}`")
    st.info(f"💡 **한국어 뜻:** {current_item['ko']}")