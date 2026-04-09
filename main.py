import streamlit as st
import pandas as pd
import re
import plotly.express as px
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# 설정
# ============================================================
st.set_page_config(page_title="유튜브 댓글 수집기", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.stApp{background:linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%)}
.main-title{font-size:3rem;font-weight:800;text-align:center;
background:linear-gradient(120deg,#FF0050,#FF4081);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub-title{text-align:center;color:#888;margin-bottom:2rem}
.glass-card{background:rgba(255,255,255,0.8);border-radius:16px;padding:24px;
margin-bottom:16px;box-shadow:0 8px 32px rgba(0,0,0,0.06)}
.comment-card{background:rgba(255,255,255,0.9);border-radius:14px;padding:18px 22px;
margin-bottom:10px;box-shadow:0 4px 16px rgba(0,0,0,0.04);
border-left:4px solid #FF4081}
.reply-box{background:#f8f0ff;border-left:3px solid #c084fc;border-radius:10px;
padding:12px 16px;margin:4px 0 8px 20px;font-size:0.88rem}
.like-tag{background:linear-gradient(135deg,#FF4081,#FF0050);color:#fff;
padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600}
.sbox{color:#fff;border-radius:16px;padding:18px;text-align:center}
.sbox .num{font-size:1.8rem;font-weight:800}
.sbox .lbl{font-size:0.85rem;opacity:0.9}
.s1{background:linear-gradient(135deg,#667eea,#764ba2)}
.s2{background:linear-gradient(135deg,#f093fb,#f5576c)}
.s3{background:linear-gradient(135deg,#4facfe,#00f2fe)}
.s4{background:linear-gradient(135deg,#f6d365,#fda085)}
.divider{height:3px;background:linear-gradient(90deg,transparent,#FF4081,transparent);
border:none;margin:2rem 0}
.pos{background:#e8f5e9;color:#2e7d32;padding:2px 10px;border-radius:12px;font-size:0.75rem}
.neg{background:#fce4ec;color:#c62828;padding:2px 10px;border-radius:12px;font-size:0.75rem}
.neu{background:#f3f4f6;color:#666;padding:2px 10px;border-radius:12px;font-size:0.75rem}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#1a1a2e,#16213e,#0f3460)}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{color:#fff!important}
section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] li{color:#ccc!important}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 함수
# ============================================================
def get_api_key():
    try:
        return st.secrets["YOUTUBE_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None

def extract_video_id(url):
    for p in [r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
              r'youtu\.be/([a-zA-Z0-9_-]{11})',
              r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
              r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
              r'^([a-zA-Z0-9_-]{11})$']:
        m = re.search(p, url.strip())
        if m:
            return m.group(1)
    return None

def fmt(n):
    if n >= 1e8: return f"{n/1e8:.1f}억"
    if n >= 1e4: return f"{n/1e4:.1f}만"
    if n >= 1e3: return f"{n/1e3:.1f}천"
    return f"{n:,}"

def get_video_info(yt, vid):
    try:
        r = yt.videos().list(part="snippet,statistics", id=vid).execute()
        if r["items"]:
            s, t = r["items"][0]["snippet"], r["items"][0]["statistics"]
            return dict(title=s.get("title",""), channel=s.get("channelTitle",""),
                        published=s.get("publishedAt","")[:10],
                        thumb=s["thumbnails"].get("high",{}).get("url",""),
                        views=int(t.get("viewCount",0)), likes=int(t.get("likeCount",0)),
                        comments=int(t.get("commentCount",0)))
    except HttpError as e:
        st.error(f"영상 정보 오류: {e}")
    return None

def get_comments(yt, vid, mx=200, order="relevance"):
    out, tok = [], None
    try:
        while len(out) < mx:
            r = yt.commentThreads().list(
                part="snippet,replies", videoId=vid,
                maxResults=min(100, mx-len(out)),
                pageToken=tok, order=order, textFormat="plainText").execute()
            for item in r.get("items",[]):
                sn = item["snippet"]["topLevelComment"]["snippet"]
                rc = item["snippet"].get("totalReplyCount",0)
                reps = []
                if rc > 0 and item.get("replies"):
                    for rr in item["replies"]["comments"]:
                        rs = rr["snippet"]
                        reps.append(dict(author=rs.get("authorDisplayName",""),
                                         text=rs.get("textDisplay",""),
                                         likes=rs.get("likeCount",0),
                                         date=rs.get("publishedAt","")[:10]))
                out.append(dict(작성자=sn.get("authorDisplayName",""),
                                댓글=sn.get("textDisplay",""),
                                좋아요=sn.get("likeCount",0),
                                작성일=sn.get("publishedAt","")[:10],
                                대댓글수=rc, 대댓글=reps,
                                글자수=len(sn.get("textDisplay",""))))
            tok = r.get("nextPageToken")
            if not tok: break
        return out
    except HttpError as e:
        if "commentsDisabled" in str(e):
            st.error("이 영상은 댓글이 비활성화되어 있습니다.")
        else:
            st.error(f"댓글 오류: {e}")
        return []

def sentiment(t):
    pos = ['좋아','최고','대박','감동','사랑','멋지','재밌','행복','감사','응원','ㅋㅋ','ㅎㅎ',
           '귀엽','짱','레전드','인정','완벽','good','great','best','love','amazing','awesome']
    neg = ['싫어','최악','별로','실망','짜증','화나','슬프','쓰레기','노잼','답답','혐오',
           'bad','worst','hate','terrible','boring']
    lo = t.lower()
    p = sum(1 for w in pos if w in lo)
    n = sum(1 for w in neg if w in lo)
    if p > n: return "긍정 😊"
    if n > p: return "부정 😞"
    return "중립 😐"

def sent_cls(s):
    if "긍정" in s: return "pos"
    if "부정" in s: return "neg"
    return "neu"

def keywords(texts, n=25):
    stops = set("그 저 이 것 수 를 에 의 가 은 는 으로 도 와 과 다 에서 한 하 있 없 않 더 때 되 로 해 들 좀 너무 진짜 정말 제 내 나 거 게 같 인데 이거 그냥 아 네 왜 뭐 또 안 잘 못 합니다 하는 저는 나는 제가 근데 이건 the a an is are to of and in that it for on with".split())
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', " ".join(texts))
    words = [w.lower() for w in words if w.lower() not in stops]
    return Counter(words).most_common(n)


# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("## 🛠️ 설정")
    st.markdown("---")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input("🔑 API Key", type="password", placeholder="API키 입력...")
    if api_key: st.success("✅ 연결됨")
    else: st.warning("API키를 입력하세요")
    st.markdown("---")
    mx = st.slider("최대 댓글수", 10, 500, 150, 10)
    api_ord = st.radio("정렬", ["관련성순","최신순"])
    omap = {"관련성순":"relevance","최신순":"time"}
    do_reply = st.checkbox("대댓글 보기", True)
    do_sent = st.checkbox("감정 분석", True)
    st.markdown("---")
    with st.expander("📖 API키 발급"):
        st.markdown("1. [Google Cloud Console](https://console.cloud.google.com/) 접속\n"
                    "2. 프로젝트 생성\n3. YouTube Data API v3 활성화\n4. API키 생성")

# ============================================================
# 메인 헤더 + 입력
# ============================================================
st.markdown('<p class="main-title">🎬 유튜브 댓글 수집기</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">링크 하나로 댓글 수집 · 감정분석 · 키워드 · 시각화</p>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

c1, c2 = st.columns([4,1])
with c1:
    url = st.text_input("링크", placeholder="https://www.youtube.com/watch?v=... 🔗", label_visibility="collapsed")
with c2:
    go_btn = st.button("🔍 수집", type="primary", use_container_width=True)

# ============================================================
# 수집
# ============================================================
if go_btn:
    if not api_key: st.error("❌ API키 입력!"); st.stop()
    if not url: st.error("❌ 링크 입력!"); st.stop()
    vid = extract_video_id(url)
    if not vid: st.error("❌ 올바른 링크가 아닙니다!"); st.stop()
    try:
        yt = build("youtube","v3",developerKey=api_key)
    except Exception as e:
        st.error(f"API연결 실패: {e}"); st.stop()
    with st.spinner("📡 영상 정보..."):
        vi = get_video_info(yt, vid)
    if not vi: st.error("영상 없음"); st.stop()
    with st.spinner(f"💬 댓글 수집 중 (최대 {mx}개)..."):
        cmts = get_comments(yt, vid, mx, omap[api_ord])
    if not cmts: st.stop()
    df = pd.DataFrame(cmts)
    if do_sent: df["감정"] = df["댓글"].apply(sentiment)
    st.session_state.update(df=df, vi=vi, vid=vid, do_sent=do_sent, do_reply=do_reply)

# ============================================================
# 결과
# ============================================================
if "df" not in st.session_state:
    st.markdown("""<div class="glass-card" style="text-align:center;padding:60px">
    <p style="font-size:3rem">🎬</p>
    <p style="font-size:1.3rem;font-weight:600;color:#333">유튜브 링크를 입력하고 수집하세요!</p>
    <p style="color:#999">댓글 · 감정분석 · 키워드 · 시각화</p></div>""", unsafe_allow_html=True)
    st.stop()

df = st.session_state["df"]
vi = st.session_state["vi"]
vid = st.session_state["vid"]
do_sent = st.session_state.get("do_sent", True)
do_reply = st.session_state.get("do_reply", True)

# 영상 정보
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
v1, v2 = st.columns([1,2])
with v1:
    if vi["thumb"]: st.image(vi["thumb"], use_container_width=True)
with v2:
    st.markdown(f"### {vi['title']}")
    st.markdown(f"📺 **{vi['channel']}** · 📅 {vi['published']}")
    s1,s2,s3,s4 = st.columns(4)
    s1.markdown(f'<div class="sbox s1"><div class="lbl">👀 조회수</div><div class="num">{fmt(vi["views"])}</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="sbox s2"><div class="lbl">👍 좋아요</div><div class="num">{fmt(vi["likes"])}</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="sbox s3"><div class="lbl">💬 댓글</div><div class="num">{fmt(vi["comments"])}</div></div>', unsafe_allow_html=True)
    eng = (vi["comments"]/vi["views"]*100) if vi["views"]>0 else 0
    s4.markdown(f'<div class="sbox s4"><div class="lbl">📈 참여율</div><div class="num">{eng:.2f}%</div></div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.success(f"✅ **{len(df)}개** 댓글 수집 완료!")

# ════════════════════════════════════════
# 탭
# ════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 댓글","📊 통계","🔑 키워드","😊 감정","📥 다운로드"])

# ── 탭1: 댓글 ──
with tab1:
    f1,f2,f3 = st.columns([2,1,1])
    with f1: kw = st.text_input("🔎 검색", placeholder="키워드...", key="sk")
    with f2: srt = st.selectbox("정렬", ["좋아요순","최신순","오래된순","긴댓글순"])
    with f3:
        sf = "전체"
        if do_sent and "감정" in df.columns:
            sf = st.selectbox("감정", ["전체","긍정 😊","부정 😞","중립 😐"])

    fd = df.copy()
    if kw: fd = fd[fd["댓글"].str.contains(kw, case=False, na=False)]
    if sf != "전체" and "감정" in fd.columns: fd = fd[fd["감정"]==sf]
    sm = {"좋아요순":("좋아요",False),"최신순":("작성일",False),"오래된순":("작성일",True),"긴댓글순":("글자수",False)}
    col,asc = sm[srt]
    fd = fd.sort_values(col, ascending=asc).reset_index(drop=True)
    st.info(f"📝 **{len(fd)}개** 댓글")

    pp = 20
    tp = max(1,(len(fd)-1)//pp+1)
    pg = st.number_input("페이지",1,tp,1,key="p1")
    si,ei = (pg-1)*pp, min(pg*pp,len(fd))

    for _,row in fd.iloc[si:ei].iterrows():
        sh = ""
        if do_sent and "감정" in df.columns:
            sh = f' <span class="{sent_cls(row["감정"])}">{row["감정"]}</span>'
        lk = f' <span class="like-tag">👍 {row["좋아요"]}</span>' if row["좋아요"]>0 else ""
        rp = f' · 💬 대댓글 {row["대댓글수"]}개' if row["대댓글수"]>0 else ""
        st.markdown(f"""<div class="comment-card">
        <div style="font-weight:700;color:#333">👤 {row["작성자"]}{sh}</div>
        <div style="color:#555;line-height:1.7;margin:8px 0">{row["댓글"]}</div>
        <div style="font-size:0.8rem;color:#999">{lk} 📅 {row["작성일"]}{rp}</div>
        </div>""", unsafe_allow_html=True)
        if do_reply and row["대댓글수"]>0 and row["대댓글"]:
            for rr in row["대댓글"]:
                st.markdown(f"""<div class="reply-box">↳ <b>{rr["author"]}</b>
                <span style="color:#999;font-size:0.8rem">👍{rr["likes"]} · {rr["date"]}</span><br>
                {rr["text"]}</div>""", unsafe_allow_html=True)
    st.caption(f"페이지 {pg}/{tp}")

# ── 탭2: 통계 ──
with tab2:
    st.markdown("### 📊 통계 대시보드")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("총 댓글",f"{len(df)}개")
    m2.metric("총 좋아요",f"{df['좋아요'].sum():,}개")
    m3.metric("평균 좋아요",f"{df['좋아요'].mean():.1f}개")
    m4.metric("평균 글자수",f"{df['글자수'].mean():.0f}자")
    st.markdown("---")

    c1,c2 = st.columns(2)
    with c1:
        dc = df["작성일"].value_counts().sort_index()
        fig1 = px.area(x=dc.index,y=dc.values,labels={"x":"날짜","y":"댓글수"},
                       color_discrete_sequence=["#FF4081"])
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10,r=10,t=30,b=10),title="📅 날짜별 댓글수")
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.histogram(df,x="좋아요",nbins=30,color_discrete_sequence=["#667eea"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10,r=10,t=30,b=10),title="👍 좋아요 분포")
        st.plotly_chart(fig2, use_container_width=True)

    c3,c4 = st.columns(2)
    with c3:
        fig3 = px.histogram(df,x="글자수",nbins=30,color_discrete_sequence=["#4facfe"])
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10,r=10,t=30,b=10),title="✍️ 글자수 분포")
        st.plotly_chart(fig3, use_container_width=True)
    with c4:
        st.markdown("#### 🏆 좋아요 TOP 10")
        top = df.nlargest(10,"좋아요")[["작성자","댓글","좋아요"]].reset_index(drop=True)
        top.index += 1
        st.dataframe(top, use_container_width=True, height=350)

# ── 탭3: 키워드 ──
with tab3:
    st.markdown("### 🔑 키워드 분석")
    kws = keywords(df["댓글"].tolist(), 25)
    if kws:
        kdf = pd.DataFrame(kws, columns=["키워드","빈도"])
        fig4 = px.bar(kdf.iloc[::-1],x="빈도",y="키워드",orientation="h",
                      color="빈도",color_continuous_scale="Pinkyl")
        fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10,r=10,t=30,b=10),height=600,showlegend=False,
                           title="상위 25개 키워드")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(kdf, use_container_width=True)
    else:
        st.info("키워드 없음")

# ── 탭4: 감정 ──
with tab4:
    st.markdown("### 😊 감정 분석")
    if do_sent and "감정" in df.columns:
        sc = df["감정"].value_counts()
        c1,c2 = st.columns(2)
        with c1:
            fig5 = px.pie(values=sc.values,names=sc.index,hole=0.45,
                          color_discrete_sequence=["#4CAF50","#FF5252","#BDBDBD"])
            fig5.update_traces(textinfo="label+percent",textfont_size=14)
            fig5.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=30,b=10))
            st.plotly_chart(fig5, use_container_width=True)
        with c2:
            for lb in sc.index:
                ct = sc[lb]
                pct = ct/len(df)*100
                if "긍정" in lb: clr="#4CAF50"
                elif "부정" in lb: clr="#FF5252"
                else: clr="#BDBDBD"
                st.markdown(f'<div style="background:#fff;border-radius:12px;padding:16px;'
                            f'margin-bottom:10px;border-left:5px solid {clr};'
                            f'box-shadow:0 2px 8px rgba(0,0,0,0.05)">'
                            f'<b style="font-size:1.2rem">{lb}</b><br>'
                            f'<span style="font-size:1.6rem;font-weight:800;color:{clr}">'
                            f'{ct}개</span> <span style="color:#999">({pct:.1f}%)</span></div>',
                            unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 감정별 평균 좋아요")
        sl = df.groupby("감정")["좋아요"].mean().reset_index()
        fig6 = px.bar(sl,x="감정",y="좋아요",color="감정",
                      color_discrete_sequence=["#4CAF50","#FF5252","#BDBDBD"])
        fig6.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(l=10,r=10,t=30,b=10),showlegend=False)
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("감정 분석을 켜고 다시 수집하세요.")

# ── 탭5: 다운로드 ──
with tab5:
    st.markdown("### 📥 다운로드")
    st.markdown("수집한 댓글을 파일로 저장하세요.")

    dl = df.drop(columns=["대댓글"], errors="ignore")

    csv = dl.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv,
                       f"comments_{vid}.csv", "text/csv",
                       use_container_width=True)

    st.markdown("---")
    json_data = dl.to_json(orient="records", force_ascii=False, indent=2)
    st.download_button("📥 JSON 다운로드", json_data,
                       f"comments_{vid}.json", "application/json",
                       use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📋 전체 데이터 미리보기")
    st.dataframe(dl, use_container_width=True, height=400)
