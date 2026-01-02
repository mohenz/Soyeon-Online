import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("🚨 오류: .env 파일을 찾을 수 없거나 API 키가 없어요!")
else:
    genai.configure(api_key=api_key)

    print("----------- [사용 가능한 모델 목록] -----------")
    try:
        # generateContent 기능을 지원하는 모델만 골라서 출력
        found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ 발견: {m.name}")
                found = True
        
        if not found:
            print("❌ 'generateContent'를 지원하는 모델을 찾을 수 없어요. API 키 권한을 확인해주세요.")
            
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        print("팁: 'pip install --upgrade google-generativeai' 명령어로 라이브러리를 업데이트 해보세요.")
    print("---------------------------------------------")
