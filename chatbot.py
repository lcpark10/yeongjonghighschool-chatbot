import os
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

# 1. .env 파일 로드
load_dotenv()

# 2. 페이지 설정
st.set_page_config(
    page_title="영종고 챗봇",
    page_icon="🏫",
    layout="centered"
)

# 3. 사이드바 디자인
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/chatbot.png", width=80) 
    st.title("영종고 챗봇")
    st.markdown("---")
    
    with st.expander("💡 사용 팁", expanded=True):
        st.write("학교생활, 학사일정, 급식 등 궁금한 점을 구체적으로 물어보세요!")
        
    with st.expander("⚠️ 주의사항", expanded=True):
        st.write("제공된 데이터를 기반으로 답변하므로 실제와 약간의 차이가 있을 수 있습니다.")
        
    st.markdown("---")
    st.caption("Powered by Groq API & Streamlit")

# 4. 메인 화면
st.title("🏫 영종고 챗봇")
st.info("안녕하세요! 궁금한 학교 정보를 무엇이든 물어보세요. 똑똑하게 답변해 드립니다. 😊")

# API 키 읽어오기 (.env 파일 또는 Streamlit Secrets)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")

# 5. CSV 데이터 로드 (인코딩 문제 완벽 대비)
@st.cache_data
def load_school_data():
    file_path = "school_data.csv"
    if not os.path.exists(file_path):
        return None

    # utf-8 -> cp949 -> euc-kr 순서로 인코딩을 시도하여 에러 방지
    for enc in ["utf-8", "cp949", "euc-kr", "utf-8-sig"]:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            return df.to_string()
        except Exception:
            continue
    return None

data_text = load_school_data()

if data_text is None:
    st.warning("⚠️ `school_data.csv` 파일을 읽을 수 없거나 파일이 없습니다. 기본 지식으로 대화를 진행합니다.")
    data_text = "별도의 제공된 학교 데이터가 없습니다."

# 시스템 프롬프트 설정
system_instruction = f"""너는 영종고등학교 담당 AI 챗봇이야. 
질문에 대해 아래 [데이터]를 바탕으로 친절하고 정확하게 한국어로 답변해줘. 데이터에 맞지 않은 잘못된 정보는 얘기하지마.

[데이터]
{data_text}"""

# 대화 기록 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": system_instruction}
    ]

# 6. 이전 대화 기록 화면 출력 (시스템 프롬프트 제외)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 7. Groq API 설정 및 답변 생성
if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
    client = Groq(api_key=GROQ_API_KEY)

    if prompt := st.chat_input("질문을 입력하세요 (예: 우리 학교 교가가 뭐야?)"):
        # 사용자 입력 UI 출력 및 저장
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # AI 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 작성하는 중입니다... 💭"):
                try:
                    # 지정하신 openai/gpt-oss-120b 모델 호출
                    chat_completion = client.chat.completions.create(
                        messages=st.session_state.messages,
                        model="openai/gpt-oss-120b",
                        temperature=0.5,
                        max_tokens=1024,
                    )
                    
                    response_text = chat_completion.choices[0].message.content
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    # 만약 지정 모델에 일시적 장애가 있을 때 대체 모델로 자동 시도하는 예외 처리
                    try:
                        chat_completion = client.chat.completions.create(
                            messages=st.session_state.messages,
                            model="llama-3.3-70b-versatile",
                            temperature=0.5,
                            max_tokens=1024,
                        )
                        response_text = chat_completion.choices[0].message.content
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    except Exception as fallback_e:
                        st.error(f"답변 생성 실패 (오류 내용): {e}")
else:
    st.error("⚠️ 올바른 Groq API 키가 설정되지 않았습니다. `.env` 파일에 `GROQ_API_KEY=gsk_...` 형태로 등록되어 있는지 확인해 주세요.")