import streamlit as st
from gtts import gTTS
import io
import re
import json

# 앱 기본 설정
st.set_page_config(page_title="스페인어 받아쓰기 연습장", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 나만의 스페인어 Daily Dictation")

# --- [1] 기본 샘플 데이터 세팅 ---
DEFAULT_TOPICS = {
    "🌱 [B1] 일상의 변화 (Sample)": [
        {"es": "Ultimamente he sentido que necesito cambiar mi estilo de vida.", "ko": "최근에 내 라이프스타일을 바꿀 필요가 있다고 느꼈어."},
        {"es": "Por eso, he empezado a hacer ejercicio todas las mañanas.", "ko": "그래서 매일 아침 운동을 하기 시작했지."},
        {"es": "Al principio fue muy dificil levantarme temprano, pero ahora me siento lleno de energia.", "ko": "처음에는 일찍 일어나는 게 너무 힘들었지만, 지금은 에너지가 넘쳐."}
    ]
}

# 세션 상태 관리
if 'topics' not in st.session_state:
    st.session_state.topics = DEFAULT_TOPICS

if 'selected_topic' not in st.session_state or st.session_state.selected_topic not in st.session_state.topics:
    st.session_state.selected_topic = list(st.session_state.topics.keys())[0]

if 'index' not in st.session_state:
    st.session_state.index = 0

if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

# --- [2] 사이드바: 주제 선택 및 파일 업로드 ---
st.sidebar.header("📚 학습 주제 선택")

topic_names = list(st.session_state.topics.keys())
# 현재 선택된 항목의 인덱스 찾기
try:
    current_nav_index = topic_names.index(st.session_state.selected_topic)
except ValueError:
    current_nav_index = 0

selected_nav = st.sidebar.selectbox("연습할 주제를 고르세요:", topic_names, index=current_nav_index)

if selected_nav != st.session_state.selected_topic:
    st.session_state.selected_topic = selected_nav
    st.session_state.index = 0
    st.session_state.show_answer = False
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
                    st.success("새 레슨이 성공적으로 등록되었습니다!")
                    st.rerun()

# 💡 이 부분이 수정되었습니다 (파일 로드 시 즉시 목록 갱신 및 주제 이동)
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
            
            # 새 주제가 추가되었으면 바로 그 주제로 변경 후 화면 새로고침
            if first_added_title:
                st.session_state.selected_topic = first_added_title
                st.session_state.index = 0
                st.session_state.show_answer = False
                st.sidebar.success("성공적으로 불러왔습니다!")
                st.rerun()
                
        except Exception as e:
            st.sidebar.error("JSON 파싱 에러! 파일 형식을 확인하세요.")

# --- [3] 유틸리티 함수 ---
def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip().lower()

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

# 입력 및 엔터 처리
with st.form(key=f"dictation_form_{st.session_state.selected_topic}_{st.session_state.index}", clear_on_submit=False):
    user_input = st.text_input(
        "스페인어로 받아 적으세요 (문장부호 생략 가능):", 
        key=f"input_{st.session_state.selected_topic}_{st.session_state.index}"
    )
    
    btn_label = "다음 문장 ➡️ (Enter)" if st.session_state.show_answer else "정답 확인 (Enter)"
    submit = st.form_submit_button(btn_label)

    if submit:
        if not st.session_state.show_answer:
            st.session_state.show_answer = True
            st.rerun()
        else:
            if st.session_state.index < len(current_story) - 1:
                st.session_state.index += 1
                st.session_state.show_answer = False
                st.rerun()
            else:
                st.success("🎉 이 레슨의 모든 문제를 끝까지 완주하셨습니다!")

# 정답 및 번역 표시
if st.session_state.show_answer:
    st.divider()
    
    user_clean = clean_text(user_input)
    answer_clean = clean_text(current_item['es'])
    
    if user_clean == answer_clean:
        st.success("🎉 **정답입니다! Perfect!**")
    else:
        st.error("❌ **아쉽네요! 스펠링을 다시 확인해보세요.**")
    
    st.markdown(f"👉 **원문 정답:** `{current_item['es']}`")
    st.info(f"💡 **한국어 뜻:** {current_item['ko']}")