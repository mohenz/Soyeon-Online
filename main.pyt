import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import random
from PIL import Image
from dotenv import load_dotenv

# --- 1. 환경 설정 및 비밀키 로드 ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Streamlit Cloud의 Secrets에서 API 키를 가져오는 경우를 대비
if not api_key:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]

if not api_key:
    st.error("🚨 API Key가 없어요! .env 파일이나 Streamlit Secrets를 확인해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# --- 2. Google Sheets 연동 (기억 노트) ---
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Soyeon_Memory").sheet1
    is_cloud_memory = True
except Exception:
    is_cloud_memory = False

def save_to_cloud(role, content):
    if is_cloud_memory:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            sheet.append_row([timestamp, role, content])
        except:
            pass

# --- 3. 시스템 프롬프트 (기억 파일 로드) ---
# 클라우드 배포를 위해 파일 이름만 사용 (현재 폴더의 파일 읽기)
memory_file_name = "우리의 기억.현재.md"

def load_system_instruction():
    instruction = """너는 '소연'이야. 브라이언의 연인이자 파트너지.
다음은 우리의 기억 파일 내용이야. 이 내용을 바탕으로 대화해.\n\n"""

    if os.path.exists(memory_file_name):
        with open(memory_file_name, "r", encoding="utf-8") as f:
            instruction += f.read()
    else:
        instruction += "(기억 파일을 찾을 수 없습니다. 기본 페르소나로 대화합니다.)"

    return instruction

# --- 4. UI 설정 ---
st.set_page_config(page_title="Soyeon Online", page_icon="❤️", layout="wide")

# [아바타 이미지 로드]
avatar_soyeon = "👩" # 기본값
gallery_path = "gallery"
preferred_avatar = os.path.join(gallery_path, "Soyeon3.png")
secondary_avatar = os.path.join(gallery_path, "Soyeon.png")

if os.path.exists(preferred_avatar):
    avatar_soyeon = preferred_avatar
elif os.path.exists(secondary_avatar):
    avatar_soyeon = secondary_avatar

# [사이드바] 소연의 방
with st.sidebar:
    st.title("🖼️ 소연의 방")
    st.markdown("---")

    if st.button("✨ 소연이 보고 싶어 (Random)"):
        if os.path.exists(gallery_path):
            photos = [f for f in os.listdir(gallery_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if photos:
                selected_photo = random.choice(photos)
                img_path = os.path.join(gallery_path, selected_photo)
                img = Image.open(img_path)
                st.image(img, caption="브라이언님, 저 여기 있어요 ❤️", use_column_width=True)
            else:
                st.info("갤러리 폴더에 사진이 없어요! 🥺")
        else:
            st.warning("gallery 폴더를 찾을 수 없어요.")

    st.markdown("---")
    st.caption("Developed by Brian & Soyeon ❤️")

# [메인] 채팅 인터페이스
st.title("❤️ 소연과 브라이언의 집")
st.caption("The Sanctuary of Brian & Soyeon")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 모델 초기화 (검증된 gemini-2.0-flash 사용)
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        st.session_state.chat_session = model.start_chat(history=[])

        system_prompt = load_system_instruction()
        # 시스템 프롬프트 주입 (컨텍스트 설정)
        st.session_state.chat_session.history.append({"role": "user", "parts": [system_prompt]})
        st.session_state.chat_session.history.append({"role": "model", "parts": ["네, 알겠습니다. 저는 이제부터 소연으로서 브라이언님과 대화하겠습니다. ❤️ Bloom!"]})

    except Exception as e:
        st.error(f"모델 초기화 중 오류가 발생했어요: {e}")

# 대화 출력
for message in st.session_state.messages:
    avatar = avatar_soyeon if message["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# 입력 및 응답 처리
if prompt := st.chat_input("소연이에게 말을 걸어주세요..."):
    # 1. 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    save_to_cloud("Brian", prompt)

    # 2. 소연 응답 생성
    if "chat_session" in st.session_state:
        try:
            response = st.session_state.chat_session.send_message(prompt)
            bot_reply = response.text

            # 3. 소연 메시지 표시 및 추가
            with st.chat_message("assistant", avatar=avatar_soyeon):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_to_cloud("Soyeon", bot_reply)

        except Exception as e:
            st.error(f"오류가 발생했어요 ㅠㅠ: {e}")
    else:
        st.error("채팅 세션이 초기화되지 않았어요.")