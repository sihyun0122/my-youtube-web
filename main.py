import streamlit as st
import pandas as pd
import re
import plotly.express as px
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(page_title="유튜브 댓글 수집기", page_icon="🎬", layout="wide")

# ============================================================
# CSS
# ============================================================
CUSTOM_CSS = """
<style>
.stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
.main-title {
    font-size:3rem; font-weight:800; text-align:center;
    background: linear-gradient(120deg,#FF0050,#FF4081,#FF6090);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.sub-title { text-align:center; color:#888; font-size:1.1rem; margin-bottom:2rem; }
.glass-card {
    background:rgba(255,255,255,0.75); backdrop-filter:blur(12px);
    border:1px solid rgba(255,255,255,0.5); border-radius:16px;
    padding:24px; margin-bottom:16px; box-shadow:0 8px 32px rgba(0,0,0,0.06);
}
.comment-card {
    background:rgba(255,255,255,0.85); border:1px solid rgba(0,0,0,0.04);
    border-radius:14px; padding:18px 22px; margin-bottom:12px;
    box-shadow:0 4px 20px rgba(0,0,0,0.04);
}
.comment-card:hover { transform:translateY(-1px); box-shadow:0 6px 24px rgba(0,0,0,0.08); }
.comment-author { font-weight:700; font-size:0.95rem; color:#333; margin-bottom:6px; }
.comment-body { color:#555; font-size:0.92rem; line-height:1.7; margin-bottom:8px; }
.comment-badge { font-size:0.75rem; color:#999; }
.like-badge {
    background:linear-gradient(135deg,#FF4081,#FF0050); color:white;
    padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600;
}
.reply-card {
    background:rgba(240,240,255,0.6); border-left:3px solid #FF4081;
    border-radius:10px; padding:12px 16px; margin:6px 0 6px 24px; font-size:0.88rem;
}
.stat-box {
    background:linear-gradient(135deg,#667eea,#764ba2); color:white;
    border-radius:16px; padding:20px; text-align:center;
}
.stat-box.red { background:linear-gradient(135deg,#f093fb,#f5576c); }
.stat-box.green { background:linear-gradient(135deg,#4facfe,#00f2fe); }
.stat-box.orange { background:linear-gradient(135deg,#f6d365,#fda085); }
.stat-number { font-size:2rem; font-weight:800; margin:4px 0; }
.stat-label { font-size:0.85rem; opacity:0.9; }
.video-title { font-size:1.4rem; font-weight:700; color:#222; margin-bottom:8px; }
.video-channel { color:#FF0050; font-weight:600; }
.video-date { color:#999; font-size:0.85rem; }
.fancy-divider {
    height:3px; background:linear-gradient(90deg,transparent,#FF4081,transparent);
    border:none; margin:2rem 0;
}
.sentiment-positive { background:#e8f5e9; color:#2e7d32; padding:3px 10px; border-radius:12px; font-size:0.75rem; }
.sentiment-negative { background:#fce4ec; color:#c62828; padding:3px 10px; border-radius:12px; font-size:0.75rem; }
.sentiment-neutral { background:#f3f4f6; color:#666; padding:3px 10px; border-radius:12px; font-size:0.75rem; }
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#1a1a2e,#16213e,#0f3460); }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color:#fff !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label { color:#ccc !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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


def format_number(n):
    if n >= 100000000:
        return f"{n/100000000:.1f}억"
    if n >= 10000:
        return f"{n/10000:.1f}만"
    if n >= 1000:
        return f"{n/1000:.1f}천"
    return f"{n:,}"


def get_video_info(youtube, video_id):
    try:
        resp = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        if resp["items"]:
            s = resp["items"][0]["snippet"]
            t = resp["items"][0]["statistics"]
            return dict(
                title=s.get("title", ""),
                channel=s.get("channelTitle", ""),
                published=s.get("publishedAt", "")[:10],
                thumbnail=s["thumbnails"].get("high", {}).get("url", ""),
                view_count=int(t.get("viewCount", 0)),
                like_count=int(t.get("likeCount", 0)),
                comment_count=int(t.get("commentCount", 0)),
            )
    except HttpError as e:
        st.error(f"영상 정보 오류: {e}")
    return None


def get_comments(youtube, video_id, max_comments=200, order="relevance"):
    comments, next_token = [], None
    try:
        while len(comments) < max_comments:
            resp = youtube.commentThreads().list(
                part="snippet,replies", videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_token, order=order, textFormat="plainText"
            ).execute()
            for item in resp.get("items", []):
                snip = item["snippet"]["topLevelComment"]["snippet"]
                rc = item["snippet"].get("totalReplyCount", 0)
                replies = []
                if rc > 0 and item.get("replies"):
                    for r in item["replies"]["comments"]:
                        rs = r["snippet"]
                        replies.append(dict(
                            작성자=rs.get("authorDisplayName", ""),
                            댓글=rs.get("textDisplay", ""),
                            좋아요=rs.get("likeCount", 0),
                            작성일=rs.get("publishedAt", "")[:10],
                        ))
                comments.append(dict(
                    작성자=snip.get("authorDisplayName", ""),
                    댓글=snip.get("textDisplay", ""),
                    좋아요=snip.get("likeCount", 0),
                    작성일=snip.get("publishedAt", "")[:10],
                    대댓글수=rc, 대댓글=replies,
                    댓글길이=len(snip.get("textDisplay", "")),
                ))
            next_token = resp.get("nextPageToken")
            if not next_token:
                break
        return comments
    except HttpError as e:
        if "commentsDisabled" in str(e):
            st.error("이 영상은 댓글이 비활성화되어 있습니다.")
        else:
            st.error(f"댓글 수집 오류: {e}")
        return []


def simple_sentiment(text):
    pos = ['좋아','최고','대박','감동','사랑','멋지','훌륭','재밌','웃기','행복',
           'good','great','best','love','amazing','awesome','감사','응원','축하',
           '기대','힐링','ㅋㅋ','ㅎㅎ','귀엽','짱','레전드','인정','공감','완벽']
    neg = ['싫어','최악','별로','실망','짜증','화나','슬프','나쁘',
           'bad','worst','hate','terrible','boring','쓰레기','후회','노잼','답답','혐오']
    t = text.lower()
    p = sum(1 for w in pos if w in t)
    n = sum(1 for w in neg if w in t)
    if p > n:
        return "긍정 😊"
    if n > p:
        return "부정 😞"
    return "중립 😐"


def get_sentiment_class(s):
    if "긍정" in s:
        return "sentiment-positive"
    if "부정" in s:
        return "sentiment-negative"
    return "sentiment-neutral"


def extract_keywords(texts, top_n=25):
    stops = {'그','저','이','것','수','를','에','의','가','은','는','으로','도','와','과',
             '다','에서','한','하','있','없','않','더','때','되','로','해','들','좀','너무',
             'the','a','an','is','are','to','of','and','in','that','it','for','on','with',
             '진짜','정말','제','내','나','거','게','같','인데','이거','그냥','아','네','왜',
             '뭐','또','안','잘','못','합니다','하는','저는','나는','제가','그게','근데','이건'}
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', " ".join(texts))
    words = [w.lower() for w in words if w.lower() not in stops]
    return Counter(words).most_common(top_n)


# ============================================================
# 메인
# ============================================================
def main():
    st.markdown('<p class="main-title">🎬 유튜브 댓글 수집기</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">링크 하나로 댓글 수집 · 감정분석 · 키워드 · 시각화까지</p>', unsafe_allow_html=True)

    # 사이드바
    with st.sidebar:
        st.markdown("## 🛠️ 설정")
        st.markdown("---")
        api_key = get_api_key()
        if not api_key:
            api_key = st.text_input("🔑 API Key", type="password", placeholder="YouTube API 키 입력...")
        if api_key:
            st.success("✅ API 키 연결됨")
        else:
            st.warning("API 키를 입력하세요")
        st.markdown("---")
        max_comments = st.slider("최대 댓글 수", 10, 500, 150, 10)
        api_order = st.radio("API 정렬", ["관련성순", "최신순"])
        order_map = {"관련성순": "relevance", "최신순": "time"}
        include_replies = st.checkbox("대댓글 보기", True)
        show_sentiment = st.checkbox("감정 분석", True)
        st.markdown("---")
        with st.expander("📖 API 키 발급법"):
            st.markdown("1. [Google Cloud Console](https://console.cloud.google.com/) 접속\n"
                        "2. 프로젝트 생성\n3. YouTube Data API v3 활성화\n4. API 키 생성")

    # 입력
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([4, 1])
    with c1:
        url = st.text_input("링크", placeholder="https://www.youtube.com/watch?v=... 🔗", label_visibility="collapsed")
    with c2:
        clicked = st.button("🔍 수집", type="primary", use_container_width=True)

    # 수집 실행
    if clicked:
        if not api_key:
            st.error("❌ API 키를 입력하세요!")
            return
        if not url:
            st.error("❌ 링크를 입력하세요!")
            return
        vid = extract_video_id(url)
        if not vid:
            st.error("❌ 올바른 유튜브 링크가 아닙니다!")
            return
        try:
            yt = build("youtube", "v3", developerKey=api_key)
        except Exception as e:
            st.error(f"API 연결 실패: {e}")
            return
        with st.spinner("📡 영상 정보 로딩..."):
            vi = get_video_info(yt, vid)
        if not vi:
            st.error("영상을 찾을 수 없습니다.")
            return
        with st.spinner(f"💬 댓글 수집 중 (최대 {max_comments}개)..."):
            cmts = get_comments(yt, vid, max_comments, order_map[api_order])
        if not cmts:
            return
        df = pd.DataFrame(cmts)
        if show_sentiment:
            df["감정"] = df["댓글"].apply(simple_sentiment)
        st.session_state.update(df=df, vi=vi, vid=vid, ss=show_sentiment, ir=include_replies)

    # 결과 표시
    if "df" not in st.session_state:
        st.markdown("""
        <div class="glass-card" style="text-align:center;padding:60px;">
            <p style="font-size:3rem;">🎬</p>
            <p style="font-size:1.3rem;font-weight:600;color:#333;">유튜브 링크를 입력하고 수집을 시작하세요!</p>
            <p style="color:#999;">댓글 수집 · 감정분석 · 키워드 · 시각화 한번에</p>
        </div>""", unsafe_allow_html=True)
        return

    df = st.session_state["df"]
    vi = st.session_state["vi"]
    vid = st.session_state["vid"]
    ss = st.session_state.get("ss", True)
    ir = st.session_state.get("ir", True)

    # 영상 정보 카드
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    vc1, vc2 = st.columns([1, 2])
    with vc1:
        if vi["thumbnail"]:
            st.image(vi["thumbnail"], use_container_width=True)
    with vc2:
        st.markdown(f'<p class="video-title">{vi["title"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="video-channel">📺 {vi["channel"]}</span> · <span class="video-date">📅 {vi["published"]}</span>', unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.markdown(f'<div class="stat-box"><div class="stat-label">👀 조회수</div><div class="stat-number">{format_number(vi["view_count"])}</div></div>', unsafe_allow_html=True)
        with sc2:
            st.markdown(f'<div class="stat-box red"><div class="stat-label">👍 좋아요</div><div class="stat-number">{format_number(vi["like_count"])}</div></div>', unsafe_allow_html=True)
        with sc3:
            st.markdown(f'<div class="stat-box green"><div class="stat-label">💬 댓글</div><div class="stat-number">{format_number(vi["comment_count"])}</div></div>', unsafe_allow_html=True)
        with sc4:
            eng = (vi["comment_count"]/vi["view_count"]*100) if vi["view_count"]>0 else 0
            st.markdown(f'<div class="stat-box orange"><div class="stat-label">📈 참여율</div><div class="stat-number">{eng:.2f}%</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.success(f"✅ 총 **{len(df)}개** 댓글 수집 완료!")

    # ═══════════ 탭 ═══════════
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 댓글", "📊 통계", "🔑 키워드", "😊 감정", "📥 다운로드"])

    # ── 탭1: 댓글 ──
    with tab1:
        fc1, fc2, fc3 = st.columns([2, 1, 1])
        with fc1:
            kw = st.text_input("🔎 검색", placeholder="키워드...", key="kw1")
        with fc2:
            srt = st.selectbox("정렬", ["좋아요순", "최신순", "오래된순", "긴순"])
        with fc3:
            if ss and "감정" in df.columns:
                sf = st.selectbox("감정필터", ["전체", "긍정 😊", "부정 😞", "중립 😐"])
            else:
                sf = "전체"

        fd = df.copy()
        if kw:
            fd = fd[fd["댓글"].str.contains(kw, case=False, na=False)]
        if sf != "전체" and "감정" in fd.columns:
            fd = fd[fd["감정"] == sf]
        sort_map = {"좋아요순": ("좋아요", False), "최신순": ("작성일", False),
                    "오래된순": ("작성일", True), "긴순": ("댓글길이", False)}
        col, asc = sort_map[srt]
        fd = fd.sort_values(col, ascending=asc).reset_index(drop=True)

        st.info(f"📝 **{len(fd)}개** 댓글")

        pp = 20
        tp = max(1, (len(fd)-1)//pp+1)
        pg = st.number_input("페이지", 1, tp, 1, key="pg1")
        si, ei = (pg-1)*pp, min(pg*pp, len(fd))

        for _, row in fd.iloc[si:ei].iterrows():
            sh = ""
            if ss and "감정" in df.columns:
                sh = f'<span class="{get_sentiment_class(row["감정"])}">{row["감정"]}</span>'
            lh = f'<span class="like-badge">👍 {row["좋아요"]}</span>' if row["좋아요"] > 0 else ""
            rh = f'<span class="comment-badge">💬 대댓글 {row["대댓글수"]}개</span>' if row["대댓글수"] > 0 else ""

            st.markdown(f"""<div class="comment-card">
                <div class="comment-author">👤 {row["작성자"]} {sh}</div>
                <div class="comment-body">{row["댓글"]}</div>
                <div style="display:flex;gap:12px;align-items:center;">
                    {lh}<span class="comment-badge">📅 {row["작성일"]}</span>{rh}
                </div>
            </div>""", unsafe_allow_html=True)

            if ir and row["대댓글수"] > 0 and row["대댓글"]:
                for rep in row["대댓글"]:
                    st.markdown(f"""<div class="reply-card">
                        ↳ <b>{rep["작성자"]}</b> <span style="color:#999;font-size:0.8rem;">👍 {rep["좋아요"]} · {rep["작성일"]}</span><br>
                        <span style="color:#555;">{rep["댓글"]}</span>
                    </div>""", unsafe_allow_html=True)

        st.caption(f"페이지 {pg} / {tp}")

    # ── 탭2: 통계 ──
    with tab2:
        st.markdown("### 📊 댓글 통계 대시보드")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 댓글", f"{len(df)}개")
        m2.metric("총 좋아요", f"{df['좋아요'].sum():,}개")
        m3.metric("평균 좋아요", f"{df['좋아요'].mean():.1f}개")
        m4.metric("평균 글자수", f"{df['댓글길이'].mean():.0f}자")
        st.markdown("---")

        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("#### 📅 날짜별 댓글 수")
            dc = df["작성일"].value_counts().sort_index()
            fig1 = px.area(x=dc.index, y=dc.values, labels={"x":"날짜","y":"댓글수"},
                           color_discrete_sequence=["#FF4081"])
            fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig1, use_container_width=True)
        with ch2:
            st.markdown("#### 👍 좋아요 분포")
            fig2 = px.histogram(df, x="좋아요", nbins=30, color_discrete_sequence=["#667eea"],
                                labels={"좋아요":"좋아요수","count":"댓글수"})
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig2, use_container_width=True)

        ch3, ch4 = st.columns(2)
        with ch3:
            st.markdown("#### ✍️ 댓글 길이 분포")
            fig3 = px.histogram(df, x="댓글길이", nbins=30, color_discrete_sequence=["#4facfe"],
                                labels={"댓글길이":"글자수","count":"댓글수"})
            fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig3, use_container_width=True)
        with ch4:
            st.markdown("#### 🏆 좋아요 TOP 10 댓글")
            top10 = df.nlargest(10, "좋아요")[["작성자","댓글","좋아요"]].reset_index(drop=True)
            top10.index = top10.index + 1
            st.dataframe(top10, use_container_width=True, height=350)

    # ── 탭3: 키워드 ──
    with tab3:
        st.markdown("### 🔑 키워드 분석")
        kws = extract_keywords(df["댓글"].tolist(), 25)
        if kws:
            kw_df = pd.DataFrame(kws, columns=["키워드", "빈도"])
            fig4 = px.bar(kw_df.iloc[::-1], x="빈도", y="키워드", orientation="h",
                          color="빈도", color_continuous_scale="Pinkyl",
                          labels={"빈도":"등장횟수","키워드":"키워드"})
            fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=20,r=20,t=20,b=20), height=600, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

            st.markdown("#### 📋 키워드 테이블")
            kc1, kc2 = st.columns(2)
            half = len(kw_df) // 2
            with kc1:
                st.dataframe(kw_df.iloc[:half].reset_index(drop=True), use_container_width=True)
            with kc2:
                st.dataframe(kw_df.iloc[half:].reset_index(drop=True), use_container_width=True)
        else:
            st.info("키워드를 추출할 수 없습니다.")

    # ── 탭4: 감정 ──
    with tab4:
        st.markdown("### 😊 감정 분석 결과")
        if ss and "감정" in df.columns:
            sc = df["감정"].value_counts()

            sc1, sc2 = st.columns(2)
            with sc1:
                fig5 = px.pie(values=sc.values, names=sc.index,
                              color_discrete_sequence=["#4CAF50","#FF5252","#BDBDBD"],
                              hole=0.45)
                fig5.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20,r=20,t=40,b=20))
                fig5.update_traces(textinfo="label+percent", textfont_size=14)
                st.plotly_chart(fig5, use_container_width=True)

            with sc2:
                for label in sc.index:
                    cnt = sc[label]
                    pct = cnt / len(df) * 100
                    if "긍정" in label:
                        color = "#4CAF50"
                    elif "부정" in label:
                        color = "#FF5252"
                    else:
                        color = "#BDBDBD"
                    st.markdown(f"""
                    <div style="background:white;border-radius:12px;padding:16px;margin-bottom:12px;
                                border-left:5px solid {color};box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                        <span style="font-size:1.3rem;font-weight:700;">{label}</span><br>
                        <span style="font-size:1.8rem;font-weight:800;color:{color};">{cnt}개</span>
                        <span style="color:#999;"> ({pct:.1f}%)</span>
                    </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 감정별 평균 좋아요")
            sent_likes = df.groupby("감정")["좋아요"].mean().reset_index()
            fig6 = px.bar(sent_likes, x="감정", y="좋아요",
                          color="감정", color_discrete_sequence=["#4CAF50","#FF5252","#BDBDBD"],
                          labels={"좋아요":"평균 좋아요"})
            fig6.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=20,r=20,t=20,b=20), showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("사이드바에서 '감정 분석' 옵션을 켜고 다시 수집하세요.")

    # ── 탭5: 다운로드 ──
    with tab5:
        st.markdown("### 📥 데이터 다운로드")
        st.markdown("수집한 댓글 데이터를 파일로 저장하세요.")

        dl_df = df.drop(columns
