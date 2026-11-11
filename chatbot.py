import os
import io # 문자열을 파일처럼 다루기 위해 추가
import streamlit as st
import pandas as pd
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

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

# 5. 데이터 로드 (st.secrets 우선 -> 로컬 csv 파일 차선)
@st.cache_data
def load_school_data():
    # 1순위: Streamlit Secrets에 저장된 SCHOOL_DATA 읽기
    if "SCHOOL_DATA" in st.secrets:
        try:
            raw_data = st.secrets["SCHOOL_DATA"]
            df = pd.read_csv(io.StringIO(raw_data))
            return df.to_string()
        except Exception:
            # CSV 변환 실패 시 텍스트 형태 그대로 전달
            return st.secrets["SCHOOL_DATA"]

    # 2순위: 로컬에 school_data.csv 파일이 있을 경우 읽기 (테스트용)
    file_path = "school_data.csv"
    if os.path.exists(file_path):
        for enc in ["utf-8", "cp949", "euc-kr", "utf-8-sig"]:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                return df.to_string()
            except Exception:
                continue
                
    return None

data_text = load_school_data()

if data_text is None:
    st.warning("⚠️ 제공된 학교 데이터(Streamlit Secrets 또는 CSV)를 읽을 수 없거나 파일이 없습니다. 기본 지식으로 대화를 진행합니다.")
    data_text = "별도의 제공된 학교 데이터가 없습니다."

# --- 현재 날짜 계산 (한국 표준시 기준) ---
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
today_str = f"{now.year}년 {now.month}월 {now.day}일 {weekdays[now.weekday()]}"

# --- 시스템 프롬프트 고도화 ---
system_instruction = f"""너는 영종고등학교 담당 AI 챗봇이야. 
오늘 날짜는 {today_str}입니다.

[답변 지침]
1. 아래 [데이터]를 바탕으로 친절하고 정확하게 한국어로 답변해줘. 데이터에 없는 허구의 정보는 절대 말하지 마.
2. 사용자가 특정 날짜 없이 "급식 뭐야?", "밥 뭐야?" 등으로 물어보면, 무조건 오늘 날짜({today_str})를 기준으로 오늘 급식을 찾아서 알려줘.
3. 내일이나 특정 날짜를 물어보면 해당 날짜에 맞춰서 알려줘.
4. 급식 정보가 없다면 "오늘은 급식 정보가 없습니다"라고 자연스럽게 안내해.

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

    if prompt := st.chat_input("질문을 입력하세요 (예: 오늘 학교 급식 뭐야?)"):
        # 사용자 입력 UI 출력 및 저장
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # AI 답변 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 작성하는 중입니다... 💭"):
                try:
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
    st.error("⚠️ 올바른 Groq API 키가 설정되지 않았습니다. `.env` 파일이나 Streamlit Secrets에 `GROQ_API_KEY=gsk_...` 형태로 등록되어 있는지 확인해 주세요.")
