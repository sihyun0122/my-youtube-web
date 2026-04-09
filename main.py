import streamlit as st
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import io
import json

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유튜브 댓글 수집기",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 전체 스타일 (밝고 세련된 UI)
# ============================================================
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* 메인 헤더 */
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(120deg, #FF0050, #FF4081, #FF6090);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
        letter-spacing: -1px;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }

    /* 글래스모피즘 카드 */
    .glass-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.1);
    }

    /* 댓글 카드 */
    .comment-card {
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(0,0,0,0.04);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .comment-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(0,0,0,0.08);
        border-color: rgba(255,0,80,0.15);
    }
    .comment-author {
        font-weight: 700;
        font-size: 0.95rem;
        color: #333;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .comment-body {
        color: #555;
        font-size: 0.92rem;
        line-height: 1.7;
        margin-bottom: 8px;
        word-break: break-word;
    }
    .comment-footer {
        display: flex;
        gap: 16px;
        align-items: center;
    }
    .comment-badge {
        font-size: 0.75rem;
        color: #999;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .like-badge {
        background: linear-gradient(135deg, #FF4081, #FF0050);
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* 통계 카드 */
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(102,126,234,0.25);
    }
    .stat-box.red {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 8px 25px rgba(245,87,108,0.25);
    }
    .stat-box.green {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        box-shadow: 0 8px 25px rgba(79,172,254,0.25);
    }
    .stat-box.orange {
        background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        box-shadow: 0 8px 25px rgba(253,160,133,0.25);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 800;
        margin: 4px 0;
    }
    .stat-label {
        font-size: 0.85rem;
        opacity: 0.9;
        font-weight: 300;
    }

    /* 비디오 정보 */
    .video-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #222;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .video-channel {
        color: #FF0050;
        font-weight: 600;
        font-size: 1rem;
    }
    .video-date {
        color: #999;
        font-size: 0.85rem;
    }

    /* 사이드바 꾸미기 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown span {
        color: #ccc !important;
    }
    section[data-testid="stSidebar"] label {
        color: #ddd !important;
    }

    /* 입력 필드 */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 12px 16px;
        font-size: 1rem;
        transition: border-color 0.3s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #FF4081;
        box-shadow: 0 0 0 3px rgba(255,64,129,0.15);
    }

    /* 버튼 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF0050, #FF4081) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 32px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.5px;
        box-shadow: 0 6px 20px rgba(255,0,80,0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(255,0,80,0.4) !important;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 24px;
        font-weight: 600;
    }

    /* 다운로드 버튼 */
    .stDownloadButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        border: 2px solid #FF4081 !important;
        color: #FF4081 !important;
        background: white !important;
        transition: all 0.3s !important;
    }
    .stDownloadButton > button:hover {
        background: #FF4081 !important;
        color: white !important;
    }

    /* 구분선 */
    .fancy-divider {
        height: 3px;
        background: linear-gradient(90deg, transparent, #FF4081, transparent);
        border: none;
        margin: 2rem 0;
        border-radius: 2px;
    }

    /* 감정 뱃지 */
    .sentiment-positive {
        background: #e8f5e9;
        color: #2e7d32;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .sentiment-negative {
        background: #fce4ec;
        color: #c62828;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .sentiment-neutral {
        background: #f3f4f6;
        color: #666;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* 페이지네이션 정보 */
    .page-info {
        text-align: center;
        color: #999;
        font-size: 0.85rem;
        margin: 12px 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 유틸리티 함수들
# ============================================================

def get_api_key():
    try:
        api_key = st.secrets["YOUTUBE_API_KEY"]
        if api_key:
            return api_key
    except (KeyError, FileNotFoundError):
        pass
    return None


def extract_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None


def get_video_info(youtube, video_id):
    try:
        request = youtube.videos().list(part="snippet,statistics", id=video_id)
        response = request.execute()
        if response["items"]:
            item = response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]
            return {
                "title": snippet.get("title", "제목 없음"),
                "channel": snippet.get("channelTitle", "채널명 없음"),
                "published": snippet.get("publishedAt", "")[:10],
                "description": snippet.get("description", "")[:500],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }
        return None
    except HttpError as e:
        st.error(f"영상 정보를 가져오는 중 오류: {e}")
        return None


def get_comments(youtube, video_id, max_comments=200, order="relevance"):
    comments = []
    next_page_token = None
    try:
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                order=order,
                textFormat="plainText"
            )
            response = request.execute()
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                reply_count = item["snippet"].get("totalReplyCount", 0)

                # 대댓글 수집
                replies_list = []
                if reply_count > 0 and item.get("replies"):
                    for reply in item["replies"].get("comments", []):
                        r_snippet = reply["snippet"]
                        replies_list.append({
                            "작성자": r_snippet.get("authorDisplayName", ""),
                            "댓글": r_snippet.get("textDisplay", ""),
                            "좋아요": r_snippet.get("likeCount", 0),
                            "작성일": r_snippet.get("publishedAt", "")[:10],
                        })

                comments.append({
                    "작성자": snippet.get("authorDisplayName", ""),
                    "댓글": snippet.get("textDisplay", ""),
                    "좋아요": snippet.get("likeCount", 0),
                    "작성일": snippet.get("publishedAt", "")[:10],
                    "수정일": snippet.get("updatedAt", "")[:10],
                    "대댓글수": reply_count,
                    "대댓글": replies_list,
                    "댓글길이": len(snippet.get("textDisplay", "")),
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        return comments
    except HttpError as e:
        if "commentsDisabled" in str(e):
            st.error("⚠️ 이 영상은 댓글이 비활성화되어 있습니다.")
        elif "forbidden" in str(e).lower():
            st.error("⚠️ API 키 권한 문제입니다. YouTube Data API v3가 활성화되어 있는지 확인하세요.")
        else:
            st.error(f"댓글을 가져오는 중 오류 발생: {e}")
        return []


def simple_sentiment(text):
    """간단한 한국어/영어 감정 분석"""
    positive_words = [
        '좋아', '최고', '대박', '감동', '사랑', '멋지', '훌륭', '재밌', '웃기', '행복',
        'good', 'great', 'best', 'love', 'amazing', 'awesome', 'nice', 'beautiful',
        'wonderful', 'fantastic', 'excellent', '감사', '고마', '응원', '축하', '기대',
        '존경', '힐링', 'ㅋㅋ', 'ㅎㅎ', '👍', '❤️', '🥰', '😂', '🔥', '♥',
        '잘생', '예쁘', '귀엽', '짱', '레전드', '인정', '공감', '완벽', 'perfect',
    ]
    negative_words = [
        '싫어', '최악', '별로', '실망', '짜증', '화나', '슬프', '나쁘', '못생',
        'bad', 'worst', 'hate', 'terrible', 'awful', 'ugly', 'boring', 'stupid',
        '쓰레기', '후회', '불쾌', '역겹', '노잼', '거짓', '사기', 'ㅡㅡ', ';;',
        '그만', '답답', '어이없', '황당', '선넘', '혐오',
    ]
    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    if pos_count > neg_count:
        return "긍정 😊"
    elif neg_count > pos_count:
        return "부정 😞"
    else:
        return "중립 😐"


def get_sentiment_class(sentiment):
    if "긍정" in sentiment:
        return "sentiment-positive"
    elif "부정" in sentiment:
        return "sentiment-negative"
    return "sentiment-neutral"


def format_number(n):
    if n >= 100000000:
        return f"{n/100000000:.1f}억"
    elif n >= 10000:
        return f"{n/10000:.1f}만"
    elif n >= 1000:
        return f"{n/1000:.1f}천"
    return f"{n:,}"


def extract_keywords(comments_text, top_n=30):
    """댓글에서 자주 등장하는 단어 추출"""
    stopwords = {
        '그', '저', '이', '것', '수', '를', '에', '의', '가', '은', '는',
        '으로', '도', '와', '과', '다', '에서', '한', '하', '합니다', '있',
        '없', '않', '더', '때', '되', '대', '로', '해', '들', '좀', '너무',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'to', 'of',
        'and', 'in', 'that', 'it', 'for', 'on', 'with', 'as', 'this',
        '진짜', '정말', '제', '내', '나', '거', '게', '같', '인데', '하는',
        '이거', '그냥', '아', '네', '왜', '뭐', '또', '안', '잘', '못',
        '이건', '저는', '나는', '제가', '그게', '근데',
    }
    all_text = " ".join(comments_text)
    # 한글 2글자 이상 또는 영문 3글자 이상 단어 추출
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', all_text)
    words = [w.lower() for w in words if w.lower() not in stopwords and len(w) >= 2]
    counter = Counter(words)
    return counter.most_common(top_n)


# ============================================================
# 메인 앱
# ============================================================
def main():
    # 헤더
    st.markdown('<p class="main-title">🎬 유튜브 댓글 수집기</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">유튜브 링크 하나로 댓글 수집 · 분석 · 시각화까지 한번에</p>', unsafe_allow_html=True)

    # ─── 사이드바 ───
    with st.sidebar:
        st.markdown("## 🛠️ 설정")
        st.markdown("---")

        api_key = get_api_key()
        if not api_key:
            st.markdown("### 🔑 API 키")
            api_key = st.text_input(
                "YouTube API Key",
                type="password",
                help="Google Cloud Console에서 발급받은 API 키",
                label_visibility="collapsed",
                placeholder="API 키를 입력하세요..."
            )

        if api_key:
            st.success("✅ API 키 연결됨")
        else:
            st.warning("⬆️ API 키를 입력하세요")

        st.markdown("---")
        st.markdown("### 📊 수집 옵션")

        max_comments = st.slider(
            "최대 댓글 수",
            min_value=10, max_value=500, value=150, step=10
        )

        api_order = st.radio(
            "API 정렬 기준",
            ["관련성 높은 순", "최신순"],
            index=0,
            help="YouTube API가 댓글을 가져오는 순서"
        )
        order_map = {"관련성 높은 순": "relevance", "최신순": "time"}

        include_replies = st.checkbox("대댓글도 함께 보기", value=True)
        show_sentiment = st.checkbox("감정 분석 표시", value=True)

        st.markdown("---")
        st.markdown("### 📖 사용 가이드")
        with st.expander("API 키 발급 방법"):
            st.markdown("""
            1. [Google Cloud Console](https://console.cloud.google.com/) 접속
            2. 프로젝트 생성
            3. **YouTube Data API v3** 활성화
            4. 사용자 인증 정보 → API 키 생성
            5. 키 복사 후 여기에 붙여넣기
            """)
        with st.expander("지원하는 URL 형식"):
            st.markdown("""
            - `youtube.com/watch?v=...`
            - `youtu.be/...`
            - `youtube.com/shorts/...`
            - `youtube.com/embed/...`
            - 영상 ID만 입력도 OK
            """)

        st.markdown("---")
        st.markdown(
            "<p style='text-align:center; font-size:0.8rem; color:#666;'>"
            "Made with ❤️ by 당곡고</p>",
            unsafe_allow_html=True
        )

    # ─── 메인 영역 ───
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # 링크 입력
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        url = st.text_input(
            "유튜브 링크",
            placeholder="https://www.youtube.com/watch?v=... 링크를 붙여넣으세요 🔗",
            label_visibility="collapsed"
        )
    with col_btn:
        search_clicked = st.button("🔍 수집 시작", type="primary", use_container_width=True)

    # ─── 수집 실행 ───
    if search_clicked:
        if not api_key:
            st.error("❌ 사이드바에서 API 키를 먼저 입력해주세요!")
            return
        if not url:
            st.error("❌ 유튜브 링크를 입력해주세요!")
            return

        video_id = extract_video_id(url)
        if not video_id:
            st.error("❌ 올바른 유튜브 링크가 아닙니다!")
            return

        try:
            youtube = build("youtube", "v3", developerKey=api_key)
        except Exception as e:
            st.error(f"❌ API 연결 실패: {e}")
            return

        # ── 영상 정보 ──
        with st.spinner("📡 영상 정보를 불러오는 중..."):
            video_info = get_video_info(youtube, video_id)

        if not video_info:
            st.error("❌ 영상을 찾을 수 없습니다.")
            return

        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

        # 영상 정보 카드
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        v_col1, v_col2 = st.columns([1, 2])
        with v_col1:
            if video_info["thumbnail"]:
                st.image(video_info["thumbnail"], use_container_width=True)
        with v_col2:
            st.markdown(f'<p class="video-title">{video_info["title"]}</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p><span class="video-channel">📺 {video_info["channel"]}</span>'
                f'&nbsp;&nbsp;·&nbsp;&nbsp;'
                f'<span class="video-date">📅 {video_info["published"]}</span></p>',
                unsafe_allow_html=True
            )

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.markdown(
                    f'<div class="stat-box">'
                    f'<div class="stat-label">👀 조회수</div>'
                    f'<div class="stat-number">{format_number(video_info["view_count"])}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            with s2:
                st.markdown(
                    f'<div class="stat-box red">'
                    f'<div class="stat-label">👍 좋아요</div>'
                    f'<div class="stat-number">{format_number(video_info["like_count"])}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            with s3:
                st.markdown(
                    f'<div class="stat-box green">'
                    f'<div class="stat-label">💬 전체 댓글</div>'
                    f'<div class="stat-number">{format_number(video_info["comment_count"])}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            with s4:
                engagement = 0
                if video_info["view_count"] > 0:
                    engagement = (video_info["comment_count"] / video_info["view_count"]) * 100
                st.markdown(
                    f'<div class="stat-box orange">'
                    f'<div class="stat-label">📈 참여율</div>'
                    f'<div class="stat-number">{engagement:.2f}%</div>'
                    f'</div>', unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── 댓글 수집 ──
        with st.spinner(f"💬 댓글을 수집 중... (최대 {max_comments}개)"):
            comments = get_comments(
                youtube, video_id, max_comments,
                order=order_map[api_order]
            )

        if not comments:
            st.warning("수집된 댓글이 없습니다.")
            return

        # DataFrame 생성
        df = pd.DataFrame(comments)

        # 감정 분석 추가
        if show_sentiment:
            df["감정"] = df["댓글"].apply(simple_sentiment)

        # session_state에 저장
        st.session_state["df"] = df
        st.session_state["video_info"] = video_info
        st.session_state["video_id"] = video_id
        st.session_state["show_sentiment"] = show_sentiment
        st.session_state["include_replies"] = include_replies

    # ─── 결과 표시 (session_state) ───
    if "df" not in st.session_state:
        # 빈 상태일 때 안내
        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card" style="text-align:center; padding:60px;">
            <p style="font-size:3rem; margin-bottom:8px;">🎬</p>
            <p style="font-size:1.3rem; font-weight:600; color:#333;">유튜브 링크를 입력하고 수집을 시작하세요!</p>
            <p style="color:#999; font-size:0.95rem;">댓글 수집 · 감정 분석 · 키워드 분석 · 시각화를 한번에 제공합니다</p>
        </div>
        """, unsafe_allow_html=True)
        return

    df = st.session_state["df"]
    video_info = st.session_state["video_info"]
    video_id = st.session_state["video_id"]
    show_sentiment = st.session_state.get("show_sentiment", True)
    include_replies = st.session_state.get("include_replies", True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.success(f"✅ 총 **{len(df)}개** 댓글 수집 완료!")

    # ── 탭 구성 ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 댓글 보기
