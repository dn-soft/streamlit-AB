import streamlit as st
from openai import AzureOpenAI
import os
import json
from datetime import datetime
from typing import TypedDict, List

# Azure OpenAI 클라이언트 초기화
azure_endpoint = st.secrets["AZURE_OPENAI_ENDPOINT"]
azure_api_key = st.secrets["AZURE_OPENAI_API_KEY"]
azure_api_version = st.secrets.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
azure_deployment = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version=azure_api_version,
) if azure_api_key else None

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "당신은 도움이 되는 AI 어시스턴트입니다."
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

st.title("멀티턴 AI 채팅 테스트 (GPT 5.4)")

# 사이드바에 설정 추가
st.sidebar.title("설정")
new_system_prompt = st.sidebar.text_area("시스템 프롬프트:", value=st.session_state.system_prompt, height=100)
if new_system_prompt != st.session_state.system_prompt:
    st.session_state.system_prompt = new_system_prompt
    st.session_state.messages = []  # 시스템 프롬프트가 변경되면 대화 기록 초기화

# 추가 매개변수 설정
temperature = st.sidebar.slider("Temperature:", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
max_tokens = st.sidebar.number_input("최대 토큰 수:", min_value=1, max_value=4096, value=256, step=1)
top_p = st.sidebar.slider("Top P:", min_value=0.0, max_value=1.0, value=1.0, step=0.1)

# 대화 기록 표시
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.text_area("사용자:", value=message["content"], height=100, disabled=True, key=f"user_{idx}")
    else:
        st.text_area("AI:", value=message["content"], height=100, disabled=True, key=f"ai_{idx}")

# 응답 구조체 정의
class ChatResponse(TypedDict):
    total_round: int
    answer_count: int
    current_answer: str
    hint: List[str]
    check_answer: bool
    is_end: bool
    message: str

# 채팅 입력 폼 (Enter 키로 제출 가능, 제출 후 입력창 자동 초기화)
# 응답 대기 중에는 입력/버튼을 비활성화하여 중복 전송을 방지
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("메시지를 입력하세요:", disabled=st.session_state.is_processing)
    submitted = st.form_submit_button("전송", disabled=st.session_state.is_processing)

# 1차: 사용자 메시지 등록 + 처리중 플래그 ON, 즉시 rerun → 비활성화된 폼이 화면에 표시됨
if submitted and user_input and not st.session_state.is_processing:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.is_processing = True
    st.rerun()

# 2차: 비활성화 상태 렌더 이후 실제 API 호출
if st.session_state.is_processing:
    # GPT-5/o1/o3 계열은 max_completion_tokens를 쓰고 temperature/top_p는 기본값(1)만 허용
    try:
        with st.spinner("AI 응답 생성 중..."):
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": st.session_state.system_prompt},
                    *st.session_state.messages
                ],
                max_completion_tokens=max_tokens,
                model=azure_deployment
            )
        ai_response = response.choices[0].message.content
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response
        })
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
    finally:
        st.session_state.is_processing = False
        st.rerun()

# 대화 기록 초기화 버튼
if st.button("대화 기록 초기화"):
    st.session_state.messages = []
    st.rerun()

# 대화 내용 JSON 다운로드 버튼
if st.button("대화 내용 다운로드"):
    chat_data = {
        "system_prompt": st.session_state.system_prompt,
        "messages": st.session_state.messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p
    }
    json_string = json.dumps(chat_data, ensure_ascii=False, indent=2)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_history_{timestamp}.json"
    st.download_button(
        label="JSON 파일 다운로드",
        data=json_string,
        file_name=filename,
        mime="application/json"
    )
