import streamlit as st
import pandas as pd
import random
import os
import io

# 데이터 파일 경로 설정
DB_FILE = "students_db.csv"
RESPONSE_FILE = "responses.csv"

# 세션 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# [업데이트됨] 조별활동 경향 하위 항목 정의 (총 25문항)
tendency_items = {
    "리더형": [
        "과제가 주어지면 전체적인 목차나 방향성을 먼저 기획한다.",
        "조원들의 의견이 충돌할 때 중재하고 결론을 도출하는 편이다.",
        "일정에 맞춰 진행 상황을 점검하고 팀원들을 독려한다.",
        "역할 분담이 모호할 때 나서서 일을 배분한다.",
        "팀의 최종 결과물에 대해 강한 책임감을 느낀다."
    ],
    "분위기 메이커형": [
        "첫 모임의 어색한 분위기를 깨고 대화를 주도하는 편이다.",
        "브레인스토밍 과정에서 기발하거나 엉뚱한 아이디어를 잘 낸다.",
        "팀원들의 의견에 긍정적인 리액션을 잘해준다.",
        "딱딱한 회의보다는 자유롭고 편안한 분위기를 선호한다.",
        "조원들 간의 갈등 상황에서 유머나 부드러운 화법으로 긴장을 푼다."
    ],
    "아나운서형": [
        "완성된 자료를 바탕으로 깔끔하게 대본을 작성하는 것에 자신 있다.",
        "여러 사람 앞에서 긴장하지 않고 말을 조리 있게 잘한다.",
        "복잡한 내용을 시각 자료와 함께 타인에게 쉽게 설명할 수 있다.",
        "발표 후 이어지는 교수님이나 학우들의 질의응답에 순발력 있게 대처한다.",
        "비언어적 표현(시선 처리, 목소리 톤)을 활용해 청중을 설득하는 것을 좋아한다."
    ],
    "성실한 팔로워형": [
        "나에게 주어진 분량의 자료 조사를 데드라인 전까지 완벽하게 해낸다.",
        "조장이 정해준 규칙이나 회의 일정을 엄격하게 준수한다.",
        "회의 내용을 꼼꼼하게 기록하여 서기 역할을 수행하는 편이다.",
        "전면에 나서기보다는 팀의 기초 자료를 수집하고 팩트를 체크하는 데 능하다.",
        "PPT 제작이나 문서 편집 등 실무적인 보조 작업에 강점이 있다."
    ],
    "먼저 말 안함 형": [
        "회의 중 즉각적으로 말하기보다 다른 사람들의 의견을 끝까지 경청한다.",
        "면대면 대화보다는 카카오톡 등 텍스트를 통한 의견 교환이 훨씬 편하다.",
        "생각이나 논리가 완전히 정리되기 전에는 섣불리 발언하지 않는다.",
        "다수의 의견이 정해지면 이견 없이 조용히 따르는 편이다.",
        "조별 과제라도 여러 명이 섞이는 것보다 혼자 맡은 파트를 조용히 끝내는 것을 선호한다."
    ]
}

# 문항 평탄화 및 고정된 셔플 (앱이 재실행되어도 순서 유지)
@st.cache_data
def get_shuffled_questions():
    questions = []
    for m_type, items in tendency_items.items():
        for item in items:
            questions.append({"type": m_type, "question": item})
    random.seed(42) # 고정 시드 사용 (모든 학생에게 동일한 섞인 순서 제공)
    random.shuffle(questions)
    return questions

def load_responses():
    if os.path.exists(RESPONSE_FILE):
        return pd.read_csv(RESPONSE_FILE)
    return pd.DataFrame(columns=['이름', '학번', '소속', '성별', '희망진로', '희망복수전공', 'MBTI', '조별활동경향', '하고싶은말', '조'])

def save_response(new_data):
    df = load_responses()
    # 이미 응답한 학번이면 덮어쓰기
    if new_data['학번'] in df['학번'].values:
        df.loc[df['학번'] == new_data['학번']] = pd.Series(new_data)
    else:
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv(RESPONSE_FILE, index=False)

def auto_grouping(df):
    if len(df) == 0:
        return df
    
    # MBTI에서 E/I 추출
    df['EI'] = df['MBTI'].apply(lambda x: str(x)[0].upper() if pd.notna(x) and len(str(x)) > 0 else 'X')
    
    # 특정 학과, 성별, E/I, 성향이 몰리지 않도록 정렬
    sorted_df = df.sort_values(by=['소속', '성별', 'EI', '조별활동경향'])
    
    # 총 8개 조로 라운드 로빈 배정
    groups = []
    for i in range(len(sorted_df)):
        groups.append((i % 8) + 1)
    
    sorted_df['조'] = groups
    sorted_df = sorted_df.drop(columns=['EI'])
    sorted_df.to_csv(RESPONSE_FILE, index=False)
    return sorted_df

# UI 시작
st.title("학기 팀 프로젝트 조 편성 시스템")

# 1. 로그인 화면
if not st.session_state.logged_in and not st.session_state.is_admin:
    st.subheader("로그인")
    login_id = st.text_input("ID (이메일)")
    login_pw = st.text_input("Password (학번)", type="password")
    
    if st.button("로그인"):
        if login_id == "admin" and login_pw == "admin": # 관리자 로그인
            st.session_state.is_admin = True
            st.rerun()
        else:
            try:
                db = pd.read_csv(DB_FILE)
                # 이메일과 학번 일치 확인
                user = db[(db['E-MAIL'] == login_id) & (db['학번'].astype(str) == login_pw)]
                if not user.empty:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("이메일 또는 학번이 일치하지 않습니다.")
            except FileNotFoundError:
                st.error(f"{DB_FILE} 파일을 찾을 수 없습니다. 파일이 동일한 폴더에 있는지 확인해 주세요.")

# 2. 학생 폼 화면
elif st.session_state.logged_in:
    user = st.session_state.user_info
    st.write(f"환영합니다, **{user['이름']}** ({user['소속']}) 학생!")
    
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()
        
    st.markdown("---")
    st.subheader("개인 정보 및 성향 입력")
    
    with st.form("student_form"):
        gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        career = st.text_input("희망 진로")
        double_major = st.text_input("희망 복수전공")
        mbti = st.text_input("MBTI (예: ENFP)")
        
        st.markdown("#### 조별활동 경향 파악")
        st.caption("자신에게 해당하는 항목을 **모두** 체크해 주세요. (가장 많이 체크된 유형으로 분류됩니다)")
        
        questions = get_shuffled_questions()
        selections = []
        for q in questions:
            # 25개의 항목이 섞여서 출력됨
            if st.checkbox(q['question']):
                selections.append(q['type'])
                
        comments = st.text_area("팀 편성 시 참고할 만한 하고 싶은 말 (선택)")
        
        submit_btn = st.form_submit_button("제출하기")
        
        if submit_btn:
            if not selections:
                st.warning("조별활동 경향 항목을 최소 1개 이상 선택해 주세요.")
            else:
                # 가장 많이 선택된 성향 도출
                type_counts = pd.Series(selections).value_counts()
                dominant_type = type_counts.index[0]
                
                new_data = {
                    '이름': user['이름'],
                    '학번': user['학번'],
                    '소속': user['소속'],
                    '성별': gender,
                    '희망진로': career,
                    '희망복수전공': double_major,
                    'MBTI': mbti,
                    '조별활동경향': dominant_type,
                    '하고싶은말': comments,
                    '조': None
                }
                save_response(new_data)
                st.success(f"제출이 완료되었습니다! 분석된 귀하의 주 성향은 **'{dominant_type}'** 입니다.")

# 3. 관리자 화면
elif st.session_state.is_admin:
    st.subheader("관리자 모드")
    
    if st.button("로그아웃"):
        st.session_state.is_admin = False
        st.rerun()
        
    st.markdown("---")
    df_responses = load_responses()
    st.write(f"현재 제출 인원: {len(df_responses)}명")
    st.dataframe(df_responses)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 엑셀 다운로드
        if not df_responses.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_responses.to_excel(writer, index=False, sheet_name='Students')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=excel_data,
                file_name="student_team_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    with col2:
        if st.button("🔄 데이터 초기화"):
            if os.path.exists(RESPONSE_FILE):
                os.remove(RESPONSE_FILE)
            st.success("모든 응답 데이터가 초기화되었습니다.")
            st.rerun()
            
    with col3:
        if st.button("🎲 자동 조 편성 (8개 조)"):
            if len(df_responses) == 0:
                st.warning("편성할 데이터가 없습니다.")
            else:
                grouped_df = auto_grouping(df_responses)
                st.success("조 편성이 완료되었습니다! 새로고침 또는 엑셀 다운로드를 통해 확인하세요.")
                st.rerun()