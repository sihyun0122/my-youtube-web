import streamlit as st
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
# CSS 스타일
# ============================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(120deg, #FF0050, #FF4081, #FF6090);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.06);
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.1);
    }
    .comment-card {
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(0,0,0,0.04);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
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
    }
    .comment-body {
        color: #555;
        font-size: 0.92rem;
        line-height: 1.7;
        margin-bottom: 8px;
    }
    .comment-footer {
        display: flex;
        gap: 16px;
        align-items: center;
    }
    .comment-badge {
        font-size: 0.75rem;
        color: #999;
    }
    .like-badge {
        background: linear-gradient(135deg, #FF4081, #FF0050);
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
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
    }
    .video-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #222;
        margin-bottom: 8px;
    }
    .video-channel {
        color: #FF0050;
        font-weight: 600;
    }
    .video-date {
        color: #999;
        font-size: 0.85rem;
    }
    .fancy-divider {
        height: 3px;
        background: linear-gradient(90deg, transparent, #FF4081, transparent);
        border: none;
        margin: 2rem 0;
        border-radius: 2px;
    }
    .sentiment-positive {
        background: #e8f5e9; color: #2e7d32;
        padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
    }
    .sentiment-negative {
        background: #fce4ec; color: #c62828;
        padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
    }
    .sentiment-neutral {
        background: #f3f4f6; color: #666;
        padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;
    }
    .reply-card {
        background: rgba(240,240,255,0.6);
        border-left: 3px solid #FF4081;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0 6px 24px;
        font-size: 0.88rem;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #ccc !important;
    }
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 12px 16px;
        font-size: 1rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #FF4081;
        box-shadow: 0 0 0 3px rgba(255,64,129,0.15);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 유틸리티 함수
# ============================================================
def get_api_key():
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None


def extract_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for p in patterns:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None


def get_video_info(youtube, video_id):
    try:
        resp = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        if resp["items"]:
            s = resp["items"][0]["snippet"]
            t = resp["items"][0]["statistics"]
            return {
                "title": s.get("title", ""),
                "channel": s.get("channelTitle", ""),
                "published": s.get("publishedAt", "")[:10],
                "thumbnail": s["thumbnails"].get("high", {}).get("url", ""),
                "view_count": int(t.get("viewCount", 0)),
                "like_count": int(t.get("likeCount", 0)),
                "comment_count": int(t.get("commentCount", 0)),
            }
    except HttpError as e:
        st.error(f"영상 정보 오류: {e}")
    return None


def get_comments(youtube, video_id, max_comments=200, order="relevance"):
    comments = []
    next_token = None
    try:
        while len(comments) < max_comments:
            resp = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_token,
                order=order,
                textFormat="plainText"
            ).execute()

            for item in resp.get("items", []):
                snip = item["snippet"]["topLevelComment"]["snippet"]
                reply_count = item["snippet"].get("totalReplyCount", 0)

                replies_list = []
                if reply_count > 0 and item.get("replies"):
                    for r in item["replies"]["comments"]:
                        rs = r["snippet"]
                        replies_list.append({
                            "작성자": rs.get("authorDisplayName", ""),
                            "댓글": rs.get("textDisplay", ""),
                            "좋아요": rs.get("likeCount", 0),
                            "작성일": rs.get("publishedAt", "")[:10],
                        })

                comments.append({
                    "작성자": snip.get("authorDisplayName", ""),
                    "댓글": snip.get("textDisplay", ""),
                    "좋아요": snip.get("likeCount", 0),
                    "작성일": snip.get("publishedAt", "")[:10],
                    "대댓글수": reply_count,
                    "대댓글": replies_list,
                    "댓글길이": len(snip.get("textDisplay", "")),
                })

            next_token = resp.get("nextPageToken")
            if not next_token:
                break
        return comments
    except HttpError as e:
        if "commentsDisabled" in str(e):
            st.error("⚠️ 이 영상은 댓글이 비활성화되어 있습니다.")
        else:
            st.error(f"댓글 수집 오류: {e}")
        return []


def simple_sentiment(text):
    positive = ['좋아','최고','대박','감동','사랑','멋지','훌륭','재밌','웃기','행복',
        'good','great','best','love','amazing','awesome','감사','고마','응원',
        '축하','기대','힐링','ㅋㅋ','ㅎㅎ','👍','❤','🥰','😂','🔥',
        '잘생','예쁘','귀엽','짱','레전드','인정','공감','완벽','perfect']
    negative = ['싫어','최악','별로','실망','짜증','화나','슬프','나쁘',
        'bad','worst','hate','terrible','awful','boring',
        '쓰레기','후회','불쾌','역겹','노잼','사기','답답','어이없','황당','혐오']
    t = text.lower()
    p = sum(1 for w in positive if w in t)
    n = sum(1 for w in negative if w in t)
    if p > n:
        return "긍정 😊"
    elif n > p:
        return "부정 😞"
    return "중립 😐"


def format_number(n):
    if n >= 100000000:
        return f"{n / 100000000:.1f}억"
    elif n >= 10000:
        return f"{n / 10000:.1f}만"
    elif n >= 1000:
        return f"{n / 1000:.1f}천"
    return f"{n:,}"


def extract_keywords(texts, top_n=25):
    stopwords = {'그','저','이','것','수','를','에','의','가','은','는','으로','도',
        '와','과','다','에서','한','하','있','없','않','더','때','되','로','해',
        '들','좀','너무','the','a','an','is','are','to','of','and','in','that',
        'it','for','on','with','진짜','정말','제','내','나','거','게','같','인데',
        '이거','그냥','아','네','왜','뭐','또','안','잘','못','합니다','하는','저는',
        '나는','제가','그게','근데','이건','was','were','be'}
    all_text = " ".join(texts)
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', all_text)
    words = [w.lower() for w in words if w.lower() not in stopwords]
    return Counter(words).most_common(top_n)


def get_sentiment_class(s):
    if "긍정" in s:
        return "sentiment-positive"
    elif "부정" in s:
        return "sentiment-negative"
    return "sentiment-neutral"


# ============================================================
# 메인
# ============================================================
def main():
    st.markdown('<p class="main-title">🎬 유튜브 댓글 수집기</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">링크 하나로 댓글 수집 · 감정 분석 · 키워드 분석 · 시각화까지</p>', unsafe_allow_html=True)

    # ── 사이드바 ──
    with st.sidebar:
        st.markdown("## 🛠️ 설정")
        st.markdown("---")

        api_key = get_api_key()
        if not api_key:
            st.markdown("### 🔑 API 키")
            api_key = st.text_input("API Key", type="password", label_visibility="collapsed",
                                    placeholder="YouTube API 키 입력...")

        if api_key:
            st.success("✅ API 키 연결됨")
        else:
            st.warning("⬆️ API 키를 입력하세요")

        st.markdown("---")
        st.markdown("### 📊 수집 옵션")
        max_comments = st.slider("최대 댓글 수", 10, 500, 150, 10)
        api_order = st.radio("API 정렬", ["관련성순", "최신순"])
        order_map = {"관련성순": "relevance", "최신순": "time"}
        include_replies = st.checkbox("대댓글 보기", value=True)
        show_sentiment = st.checkbox("감정 분석", value=True)

        st.markdown("---")
        with st.expander("📖 API 키 발급법"):
            st.markdown("""
            1. [Google Cloud Console](https://console.cloud.google.com/) 접속
            2. 프로젝트 생성
            3. YouTube Data API v3 활성화
            4. 사용자 인증 정보 → API 키 생성
            """)

    # ── 입력 영역 ──
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    col_in, col_bt = st.columns([4, 1])
    with col_in:
        url = st.text_input("링크", placeholder="https://www.youtube.com/watch?v=... 🔗",
                            label_visibility="collapsed")
    with col_bt:
        clicked = st.button("🔍 수집 시작", type="primary", use_container_width=True)

    # ── 수집 ──
    if clicked:
        if not api_key:
            st.error("❌ API 키를 입력하세요!")
            return
        if not url:
            st.error("❌ 링크를 입력하세요!")
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

        with st.spinner("📡 영상 정보 로딩..."):
            video_info = get_video_info(youtube, video_id)
        if not video_info:
            st.error("❌ 영상을 찾을 수 없습니다.")
            return

        with st.spinner(f"💬 댓글 수집 중... (최대 {max_comments}개)"):
            comments = get_comments(youtube, video_id, max_comments, order_map[api_order])
        if not comments:
            st.warning("수집된 댓글이 없습니다.")
            return

        df = pd.DataFrame(comments)
        if show_sentiment:
            df["감정"] = df["댓글"].apply(simple_sentiment)

        st.session_state["df"] = df
        st.session_state["video_info"] = video_info
        st.session_state["video_id"] = video_id
        st.session_state["show_sentiment"] = show_sentiment
        st.session_state["include_replies"] = include_replies

    # ── 결과 표시 ──
    if "df" not in st.session_state:
        st.markdown("""
        <div class="glass-card" style="text-align:center; padding:60px;">
            <p style="font-size:3rem;">🎬</p>
            <p style="font-size:1.3rem; font-weight:600; color:#333;">유튜브 링크를 입력하고 수집을 시작하세요!</p>
            <p style="color:#999;">댓글 수집 · 감정 분석 · 키워드 · 시각화를 한번에 제공합니다</p>
        </div>
        """, unsafe_allow_html=True)
        return

    df = st.session_state["df"]
    video_info = st.session_state["video_info"]
    video_id = st.session_state["video_id"]
    show_sentiment = st.session_state.get("show_sentiment", True)
    include_replies = st.session_state.get("include_replies", True)

    # ── 영상 정보 ──
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    vc1, vc2 = st.columns([1, 2])
    with vc1:
        if video_info["thumbnail"]:
            st.image(video_info["thumbnail"], use_container_width=True)
    with vc2:
        st.markdown(f'<p class="video-title">{video_info["title"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="video-channel">📺 {video_info["channel"]}</span>&nbsp;&nbsp;·&nbsp;&nbsp;<span class="video-date">📅 {video_info["published"]}</span>', unsafe_allow_html=True)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-label">👀 조회수</div><div class="stat-number">{format_number(video_info["view_count"])}</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box red"><div class="stat-label">👍 좋아요</div><div class="stat-number">{format_number(video_info["like_count"])}</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box green"><div class="stat-label">💬 댓글수</div><div class="stat-number">{format_number(video_info["comment_count"])}</div></div>', unsafe_allow_html=True)
        with s4:
            eng = (video_info["comment_count"] / video_info["view_count"] * 100) if video_info["view_count"] > 0 else 0
            st.markdown(f'<div class="stat-box orange"><div class="stat-label">📈 참여율</div><div class="stat-number">{eng:.2f}%</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.success(f"✅ 총 **{len(df)}개** 댓글 수집 완료!")

    # ════════════════════════════════════════════
    # 탭
    # ════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 댓글 보기", "📊 통계 분석", "🔑 키워드 분석", "😊 감정 분석", "📥 다운로드"
    ])

    # ── 탭1: 댓글 보기 ──
    with tab1:
        t1c1, t1c2, t1c3 = st.columns([2, 1, 1])
        with t1c1:
            keyword = st.text_input("🔎 댓글 검색", placeholder="키워드 입력...", key="search_kw")
        with t1c2:
            sort_opt = st.selectbox("정렬", ["좋아요 많은 순", "최신순", "오래된 순", "댓글 긴 순"])
        with t1c3:
            if show_sentiment and "감정" in df.columns:
                filter_sent = st.selectbox("감정 필터", ["전체", "긍정 😊", "부정 😞", "중립 😐"])
            else:
                filter_sent = "전체"

        filtered = df.copy()
        if keyword:
            filtered = filtered[filtered["댓글"].str.contains(keyword, case=False, na=False)]
        if filter_sent != "전체" and "감정" in filtered.columns:
            filtered = filtered[filtered["감정"] == filter_sent]
        if sort_opt == "좋아요 많은 순":
            filtered = filtered.sort_values("좋아요", ascending=False)
        elif sort_opt == "최신순":
            filtered = filtered.sort_values("작성일", ascending=False)
        elif sort_opt == "오래된 순":
            filtered = filtered.sort_values("작성일", ascending=True)
        elif sort_opt == "댓글 긴 순":
            filtered = filtered.sort_values("댓글길이", ascending=False)
        filtered = filtered.reset_index(drop=True)

        st.info(f"📝 표시 중: **{len(filtered)}개** 댓글")

        # 페이지네이션
        per_page = 20
        total_pages = max(1, (len(filtered) - 1) // per_page + 1)
        page = st.number_input("페이지", 1, total_pages, 1, key="page_num")
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, len(filtered))

        for _, row in filtered.iloc[start_idx:end_idx].iterrows():
            sent_html = ""
            if show_sentiment and "감정" in df.columns:
                cls = get_sentiment_class(row["감정"])
                sent_html = f'<span class="{cls}">{row["감정"]}</span>'

            like_html = ""
            if row["좋아요"] > 0:
                like_html = f'<span class="like-badge">👍 {row["좋아요"]}</span>'

            reply_html = ""
            if row["대댓글수"] > 0:
                reply_html = f'<span class="comment-badge">💬 대댓글 {row["대댓글수"]}개</span>'

            st.markdown(f"""
            <div class="comment-card">
                <div class="comment-author">👤 {row["작성자"]}&nbsp;&nbsp;{sent_html}</div>
                <div class="comment-body">{row["댓글"]}</div>
                <div class="comment-footer">
                    {like_html}
                    <span class="comment-badge">📅 {row["작성일"]}</span>
                    {reply_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 대댓글 표시
            if include_replies and row["대댓글수"] > 0 and row["대댓글"]:
                for rep in row["대댓글"]:
                    st.markdown(f"""
                    <div class="reply-card">
                        ↳ <b>{rep["작성자"]}</b>&nbsp;&nbsp;
                        <span style="color:#999;font-size:0.8rem;">👍 {rep["좋아요"]} · {rep["작성일"]}</span><br>
                        <span style="color:#555;">{rep["댓글"]}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.caption(f"페이지 {page} / {total_pages}")

    # ── 탭2: 통계 분석 ──
    with tab2:
        st.markdown("### 📊 댓글 통계 대시보드")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("총 댓글 수", f"{len(df)}개")
        with m2:
            st.metric("총 좋아요", f"{df['좋아요'].sum():,}개")
        with m3:
            st.metric("평균 좋아요", f"{df['좋아요'].mean():.1f}개")
        with m4:
            st.metric("평균 글자수", f"{df['댓글길이'].mean():.0f}자")

        st.markdown("---")

        ch1, ch2 = st.columns(2)

        with ch1:
            st.markdown("#### 📅 날짜별 댓글 수")
            date_counts = df["작성일"].value_counts().sort_index()
            fig_date = px.area(
                x=date_counts.index, y=date_counts.values,
                labels={"x": "날짜", "y": "댓글 수"},
                color_discrete_sequence=["#FF4081"]
            )
            fig_date.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_date, use_container_width=True)

        with ch2:
            st.markdown("#### 👍 좋아요 분포")
            fig_like = px.histogram(
                df, x="좋아요", nbins=30,
                color_discrete_sequence=["#667eea"],
                labels={"좋아요": "좋아요 수", "count": "댓글 수"}
            )
            fig_like.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_like, use_container_width=True)

        st.markdown("---")

        ch3, ch4 = st.columns(2)

        with ch3:
            st.markdown("#### ✍️ 댓글 길이 분포")
            fig_len = px.histogram(
                df, x="댓글길이", nbins=30,
                color_discrete_sequence=["#4facfe"],
                labels={"댓글길이": "글자 수", "count": "댓글 수"}
            )
            fig_len.update_layout(
                plot_bgcolor="rgba(
