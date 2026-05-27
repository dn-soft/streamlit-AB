import streamlit as st
from openai import AzureOpenAI
import json
from datetime import datetime

# ──────────────────────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="멀티턴 AI 채팅 테스트",
    page_icon="💬",
    layout="centered",
)

# ──────────────────────────────────────────────────────────────
# Azure OpenAI 클라이언트 초기화
# ──────────────────────────────────────────────────────────────
azure_endpoint = st.secrets["AZURE_OPENAI_ENDPOINT"]
azure_api_key = st.secrets["AZURE_OPENAI_API_KEY"]
azure_api_version = st.secrets.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
azure_deployment = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version=azure_api_version,
) if azure_api_key else None

# ──────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = "당신은 도움이 되는 AI 어시스턴트입니다."
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# ──────────────────────────────────────────────────────────────
# 사이드바 — 설정 & 액션
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    new_system_prompt = st.text_area(
        "시스템 프롬프트",
        value=st.session_state.system_prompt,
        height=160,
        help="시스템 프롬프트를 변경하면 대화 기록이 초기화됩니다.",
    )
    if new_system_prompt != st.session_state.system_prompt:
        st.session_state.system_prompt = new_system_prompt
        st.session_state.messages = []
        st.rerun()

    max_tokens = st.number_input(
        "최대 토큰 수",
        min_value=1,
        max_value=4096,
        value=1024,
        step=64,
    )

    st.divider()

    st.header("📁 대화 관리")

    if st.button("🗑️ 대화 기록 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.session_state.messages:
        chat_data = {
            "system_prompt": st.session_state.system_prompt,
            "messages": st.session_state.messages,
            "max_tokens": max_tokens,
        }
        json_string = json.dumps(chat_data, ensure_ascii=False, indent=2)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="💾 대화 내용 다운로드",
            data=json_string,
            file_name=f"chat_history_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    st.caption(f"💡 메시지 {len(st.session_state.messages)}개")

# ──────────────────────────────────────────────────────────────
# 메인 — 채팅 영역
# ──────────────────────────────────────────────────────────────
st.title("💬 멀티턴 AI 채팅 테스트 (GPT 5.4)")
st.caption(f"Azure OpenAI · `{azure_deployment}`")

# 대화 기록을 채팅 버블로 렌더링 (마크다운, 자동 높이, 코드블록 지원)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 처리 중일 때 응답 자리에 placeholder 표시
if st.session_state.is_processing:
    with st.chat_message("assistant"):
        st.markdown("_생각하는 중..._ ⏳")

# 채팅 입력 (Enter 제출, 하단 고정, 처리 중에는 비활성화)
user_input = st.chat_input(
    "메시지를 입력하세요...",
    disabled=st.session_state.is_processing,
)

# 1차 rerun: 사용자 메시지 등록 + 처리중 플래그 ON
if user_input and not st.session_state.is_processing:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.is_processing = True
    st.rerun()

# 2차 rerun: 비활성화 상태 렌더 후 실제 API 호출
# GPT-5/o1/o3 계열은 max_completion_tokens 사용, temperature/top_p는 기본값(1)만 허용
if st.session_state.is_processing:
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": st.session_state.system_prompt},
                *st.session_state.messages,
            ],
            max_completion_tokens=max_tokens,
            model=azure_deployment,
        )
        ai_response = response.choices[0].message.content
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response,
        })
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        st.session_state.is_processing = False
        st.rerun()
