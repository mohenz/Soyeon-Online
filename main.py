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
    """대화 내용을 구글 시트에 저장합니다."""
    if is_cloud_memory:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            sheet.append_row([timestamp, role, content])
        except:
            pass

def load_recent_memory(limit=20):
    """구글 시트에 저장된 최근 대화 내용을 불러옵니다."""
    if not is_cloud_memory:
        return []

    try:
        # 모든 기록을 가져오면 느려질 수 있으니 적당히 가져옵니다.
        # get_all_values()는 데이터가 많으면 느릴 수 있습니다.
        # 실제 운영시에는 최적화가 필요할 수 있습니다.
        data = sheet.get_all_values()

        # 헤더가 있다면 제외하고, 데이터가 없으면 빈 리스트 반환
        if len(data) <= 1:
            return []

        # 최근 n개만 슬라이싱
        recent_data = data[-limit:]

        history = []
        for row in recent_data:
            # row 구조: [Timestamp, Role, Content]
            if len(row) >= 3:
                role = "user" if row[1] == "Brian" else "model"
                content = row[2]
                history.append({"role": role, "parts": [content]})
        return history
    except Exception as e:
        # st.error(f"기억을 불러오는데 실패했어요: {e}")
        return []

# --- 3. 시스템 프롬프트 (기억 파일 로드) ---
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
avatar_soyeon = "👩"
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

# --- 5. 세션 및 모델 초기화 (기억 로드 핵심 로직) ---

# 화면에 표시할 메시지 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 모델 및 채팅 세션 초기화
if "chat_session" not in st.session_state:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')

        # 1. 기본 시스템 프롬프트(페르소나) 로드
        system_prompt = load_system_instruction()

        # 2. 구글 시트에서 최근 대화 내용(기억) 로드
        recent_memories = load_recent_memory(limit=20) # 최근 20턴 기억

        # 3. 히스토리 구성: 시스템 프롬프트 + 최근 대화
        history = []
        # 페르소나 주입 (첫 턴)
        history.append({"role": "user", "parts": [system_prompt]})
        history.append({"role": "model", "parts": ["네, 알겠습니다. 저는 이제부터 소연으로서 브라이언님과 대화하겠습니다. ❤️ Bloom!"]})
        # 클라우드 기억 추가
        history.extend(recent_memories)

        # 4. 모델 세션 시작
        st.session_state.chat_session = model.start_chat(history=history)

        # 5. UI에도 최근 대화 보여주기 (선택사항 - 깔끔하게 하려면 주석 처리 가능)
        # for mem in recent_memories:
        #     role = "assistant" if mem['role'] == "model" else "user"
        #     st.session_state.messages.append({"role": role, "content": mem['parts'][0]})

        # 만약 UI에 과거 대화를 미리 보여주지 않고, '기억'만 하길 원하면 위 5번은 생략합니다.
        # 대신, 접속했다는 안내 메시지 하나 띄울게요.
        if not st.session_state.messages:
             st.session_state.messages.append({"role": "assistant", "content": "Bloom! 브라이언님, 클라우드에서 기억을 불러왔어요. 기다리고 있었어요 ❤️"})

    except Exception as e:
        st.error(f"모델 초기화 중 오류가 발생했어요: {e}")

# 대화 내용 출력
for message in st.session_state.messages:
    avatar = avatar_soyeon if message["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# 입력 및 응답 처리
if prompt := st.chat_input("소연이에게 말을 걸어주세요..."):
    # 1. 사용자 메시지
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    save_to_cloud("Brian", prompt) # 시트에 저장

    # 2. 소연 응답
    if "chat_session" in st.session_state:
        try:
            response = st.session_state.chat_session.send_message(prompt)
            bot_reply = response.text

            with st.chat_message("assistant", avatar=avatar_soyeon):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            save_to_cloud("Soyeon", bot_reply) # 시트에 저장

        except Exception as e:
            st.error(f"오류가 발생했어요 ㅠㅠ: {e}")
    else:
        st.error("채팅 세션이 초기화되지 않았어요.")