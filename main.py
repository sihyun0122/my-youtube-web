import streamlit as st, pandas as pd, re, plotly.express as px
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="YT댓글분석기",page_icon="🎬",layout="wide")
# ── CSS ──
st.markdown("""<style>
.stApp{background:linear-gradient(160deg,#0f0c29,#302b63,#24243e)}
*{color:#e0e0e0}
.T{font-size:3.2rem;font-weight:900;text-align:center;padding:20px 0;
background:linear-gradient(90deg,#f7797d,#FBD786,#C6FFDD);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.S{text-align:center;color:#aaa;margin-bottom:2rem;font-size:1.05rem}
.G{background:rgba(255,255,255,.06);backdrop-filter:blur(16px);
border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:24px;margin-bottom:16px}
.C{background:rgba(255,255,255,.07);border-radius:16px;padding:16px 20px;
margin-bottom:10px;border-left:4px solid #f7797d;transition:.2s}
.C:hover{background:rgba(255,255,255,.12);transform:translateX(4px)}
.R{background:rgba(255,255,255,.04);border-left:3px solid #C6FFDD;
border-radius:12px;padding:10px 14px;margin:4px 0 6px 20px;font-size:.85rem}
.LK{background:linear-gradient(135deg,#f7797d,#FBD786);color:#000;
padding:2px 10px;border-radius:20px;font-size:.73rem;font-weight:700}
.B{border-radius:18px;padding:18px;text-align:center;color:#fff}
.B1{background:linear-gradient(135deg,#667eea,#764ba2)}
.B2{background:linear-gradient(135deg,#f093fb,#f5576c)}
.B3{background:linear-gradient(135deg,#4facfe,#00f2fe)}
.B4{background:linear-gradient(135deg,#f6d365,#fda085)}
.BN{font-size:1.9rem;font-weight:800}.BL{font-size:.82rem;opacity:.85}
.D{height:2px;background:linear-gradient(90deg,transparent,#f7797d,#FBD786,#C6FFDD,transparent);
border:none;margin:1.8rem 0}
.P{background:#1b5e20;color:#a5d6a7;padding:2px 10px;border-radius:12px;font-size:.73rem}
.N{background:#b71c1c;color:#ef9a9a;padding:2px 10px;border-radius:12px;font-size:.73rem}
.U{background:#333;color:#999;padding:2px 10px;border-radius:12px;font-size:.73rem}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a0a1a,#1a1a3e)}
section[data-testid="stSidebar"] *{color:#ccc!important}
div[data-testid="stMetric"]{background:rgba(255,255,255,.05);border-radius:14px;padding:12px}
div[data-testid="stMetric"] label{color:#aaa!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#fff!important;font-weight:700}
.stTabs [data-baseweb="tab"]{color:#ccc;font-weight:600}
.stTabs [aria-selected="true"]{color:#FBD786!important;border-color:#f7797d!important}
</style>""",unsafe_allow_html=True)

# ── 함수 ──
def api_key():
    try:return st.secrets["YOUTUBE_API_KEY"]
    except:return None

def vid_id(u):
    for p in[r'v=([a-zA-Z0-9_-]{11})',r'youtu\.be/([a-zA-Z0-9_-]{11})',
             r'shorts/([a-zA-Z0-9_-]{11})',r'embed/([a-zA-Z0-9_-]{11})',r'^([a-zA-Z0-9_-]{11})$']:
        m=re.search(p,u.strip())
        if m:return m.group(1)

def fm(n):
    if n>=1e8:return f"{n/1e8:.1f}억"
    if n>=1e4:return f"{n/1e4:.1f}만"
    if n>=1e3:return f"{n/1e3:.1f}천"
    return f"{n:,}"

def vinfo(yt,v):
    try:
        r=yt.videos().list(part="snippet,statistics",id=v).execute()
        if r["items"]:
            s,t=r["items"][0]["snippet"],r["items"][0]["statistics"]
            return dict(t=s.get("title",""),ch=s.get("channelTitle",""),
                d=s.get("publishedAt","")[:10],img=s["thumbnails"].get("high",{}).get("url",""),
                vc=int(t.get("viewCount",0)),lc=int(t.get("likeCount",0)),
                cc=int(t.get("commentCount",0)))
    except:pass

def fetch(yt,v,mx=200,od="relevance"):
    out,tk=[],None
    try:
        while len(out)<mx:
            r=yt.commentThreads().list(part="snippet,replies",videoId=v,
                maxResults=min(100,mx-len(out)),pageToken=tk,order=od,textFormat="plainText").execute()
            for i in r.get("items",[]):
                sn=i["snippet"]["topLevelComment"]["snippet"]
                rc=i["snippet"].get("totalReplyCount",0)
                rps=[]
                if rc>0 and i.get("replies"):
                    for rr in i["replies"]["comments"]:
                        rs=rr["snippet"]
                        rps.append(dict(a=rs.get("authorDisplayName",""),t=rs.get("textDisplay",""),
                            l=rs.get("likeCount",0),d=rs.get("publishedAt","")[:10]))
                out.append(dict(작성자=sn.get("authorDisplayName",""),댓글=sn.get("textDisplay",""),
                    좋아요=sn.get("likeCount",0),작성일=sn.get("publishedAt","")[:10],
                    대댓글수=rc,rps=rps,글자수=len(sn.get("textDisplay",""))))
            tk=r.get("nextPageToken")
            if not tk:break
        return out
    except HttpError as e:
        if "commentsDisabled" in str(e):st.error("댓글 비활성화 영상입니다.")
        else:st.error(f"오류: {e}")
        return[]

def senti(t):
    lo=t.lower()
    p=sum(1 for w in['좋아','최고','대박','감동','사랑','멋지','재밌','행복','감사','응원',
        'ㅋㅋ','ㅎㅎ','귀엽','짱','레전드','인정','완벽','good','great','love','amazing',
        'awesome','best','nice','beautiful','fantastic','excellent','힐링','축하','기대']if w in lo)
    n=sum(1 for w in['싫어','최악','별로','실망','짜증','화나','슬프','쓰레기','노잼','답답',
        '혐오','bad','worst','hate','terrible','boring','awful','stupid','ugly']if w in lo)
    if p>n:return"긍정 😊"
    if n>p:return"부정 😞"
    return"중립 😐"

def scls(s):
    if"긍정"in s:return"P"
    if"부정"in s:return"N"
    return"U"

def kw(texts,n=25):
    st_=set("그 저 이 것 수 를 에 의 가 은 는 도 와 다 한 하 있 없 않 더 때 되 로 해 들 좀 너무 진짜 정말 제 내 나 거 게 같 인데 이거 그냥 아 네 왜 뭐 또 안 잘 못 합니다 하는 저는 나는 근데 이건 the a an is are to of and in that it for on with was be".split())
    ws=re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}'," ".join(texts))
    ws=[w.lower()for w in ws if w.lower()not in st_]
    return Counter(ws).most_common(n)

# ── 사이드바 ──
with st.sidebar:
    st.markdown("## ⚙️ 설정")
    key=api_key()
    if not key:key=st.text_input("🔑 API Key",type="password",placeholder="API키 입력...")
    if key:st.success("✅ 연결됨")
    else:st.warning("API키 필요")
    st.markdown("---")
    mx=st.slider("최대 댓글",10,500,150,10)
    od=st.radio("정렬",["관련성","최신"])
    om={"관련성":"relevance","최신":"time"}
    dr=st.checkbox("대댓글",True)
    ds=st.checkbox("감정분석",True)
    st.markdown("---")
    with st.expander("📖 API키 발급"):
        st.markdown("1.[Google Cloud Console](https://console.cloud.google.com) 접속\n"
                    "2.프로젝트 생성\n3.YouTube Data API v3 활성화\n4.API키 생성")

# ── 헤더 ──
st.markdown('<p class="T">🎬 YouTube 댓글 분석기</p>',unsafe_allow_html=True)
st.markdown('<p class="S">댓글수집 · 감정분석 · 키워드추출 · 통계시각화 · 다운로드</p>',unsafe_allow_html=True)
st.markdown('<div class="D"></div>',unsafe_allow_html=True)

c1,c2=st.columns([5,1])
with c1:url=st.text_input("u",placeholder="유튜브 링크를 붙여넣으세요 🔗",label_visibility="collapsed")
with c2:go=st.button("🚀 분석",type="primary",use_container_width=True)

# ── 수집 ──
if go:
    if not key:st.error("❌ API키!");st.stop()
    if not url:st.error("❌ 링크!");st.stop()
    v=vid_id(url)
    if not v:st.error("❌ 잘못된 링크!");st.stop()
    try:yt=build("youtube","v3",developerKey=key)
    except Exception as e:st.error(f"연결실패:{e}");st.stop()
    with st.spinner("📡 영상 정보..."):vi=vinfo(yt,v)
    if not vi:st.error("영상없음");st.stop()
    with st.spinner(f"💬 댓글 수집중({mx}개)..."):cm=fetch(yt,v,mx,om[od])
    if not cm:st.stop()
    df=pd.DataFrame(cm)
    if ds:df["감정"]=df["댓글"].apply(senti)
    st.session_state.update(df=df,vi=vi,v=v,ds=ds,dr=dr)

if "df" not in st.session_state:
    st.markdown("""<div class="G" style="text-align:center;padding:80px 20px">
    <p style="font-size:4rem;margin:0">🎬</p>
    <p style="font-size:1.4rem;font-weight:700;color:#fff;margin:12px 0">유튜브 링크를 입력하세요</p>
    <p style="color:#888">댓글 수집부터 AI 감정분석까지 한번에</p></div>""",unsafe_allow_html=True)
    st.stop()

df=st.session_state["df"];vi=st.session_state["vi"]
v=st.session_state["v"];ds=st.session_state.get("ds",True);dr=st.session_state.get("dr",True)

# ── 영상정보 ──
st.markdown('<div class="D"></div>',unsafe_allow_html=True)
st.markdown('<div class="G">',unsafe_allow_html=True)
a,b=st.columns([1,2])
with a:
    if vi["img"]:st.image(vi["img"],use_container_width=True)
with b:
    st.markdown(f"### 🎬 {vi['t']}")
    st.markdown(f"📺 **{vi['ch']}** &nbsp;·&nbsp; 📅 {vi['d']}")
    x1,x2,x3,x4=st.columns(4)
    x1.markdown(f'<div class="B B1"><div class="BL">👀 조회수</div><div class="BN">{fm(vi["vc"])}</div></div>',unsafe_allow_html=True)
    x2.markdown(f'<div class="B B2"><div class="BL">👍 좋아요</div><div class="BN">{fm(vi["lc"])}</div></div>',unsafe_allow_html=True)
    x3.markdown(f'<div class="B B3"><div class="BL">💬 댓글</div><div class="BN">{fm(vi["cc"])}</div></div>',unsafe_allow_html=True)
    eg=(vi["cc"]/vi["vc"]*100)if vi["vc"]>0 else 0
    x4.markdown(f'<div class="B B4"><div class="BL">📈 참여율</div><div class="BN">{eg:.2f}%</div></div>',unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)
st.markdown('<div class="D"></div>',unsafe_allow_html=True)
st.success(f"✅ **{len(df)}개** 댓글 수집완료!")

# ═══ 탭 ═══
t1,t2,t3,t4,t5=st.tabs(["💬 댓글","📊 통계","🔑 키워드","😊 감정","📥 다운로드"])

with t1:
    f1,f2,f3=st.columns([2,1,1])
    with f1:q=st.text_input("🔎",placeholder="검색...",key="q")
    with f2:so=st.selectbox("정렬",["좋아요순","최신순","오래된순","긴댓글순"])
    with f3:
        sf="전체"
        if ds and"감정"in df.columns:sf=st.selectbox("감정",["전체","긍정 😊","부정 😞","중립 😐"])
    fd=df.copy()
    if q:fd=fd[fd["댓글"].str.contains(q,case=False,na=False)]
    if sf!="전체"and"감정"in fd.columns:fd=fd[fd["감정"]==sf]
    sm={"좋아요순":("좋아요",False),"최신순":("작성일",False),"오래된순":("작성일",True),"긴댓글순":("글자수",False)}
    co,ac=sm[so];fd=fd.sort_values(co,ascending=ac).reset_index(drop=True)
    st.info(f"**{len(fd)}개** 댓글")
    pp=20;tp=max(1,(len(fd)-1)//pp+1)
    pg=st.number_input("페이지",1,tp,1,key="pg")
    si,ei=(pg-1)*pp,min(pg*pp,len(fd))
    for _,r in fd.iloc[si:ei].iterrows():
        sh=""
        if ds and"감정"in df.columns:sh=f' <span class="{scls(r["감정"])}">{r["감정"]}</span>'
        lk=f'<span class="LK">👍{r["좋아요"]}</span> 'if r["좋아요"]>0 else""
        rp=f' · 💬대댓글{r["대댓글수"]}개'if r["대댓글수"]>0 else""
        st.markdown(f'<div class="C"><b>👤 {r["작성자"]}</b>{sh}<br>'
            f'<span style="color:#ccc;line-height:1.8">{r["댓글"]}</span><br>'
            f'<span style="font-size:.78rem;color:#888">{lk}📅{r["작성일"]}{rp}</span></div>',unsafe_allow_html=True)
        if dr and r["대댓글수"]>0 and r["rps"]:
            for rr in r["rps"]:
                st.markdown(f'<div class="R">↳ <b>{rr["a"]}</b> '
                    f'<span style="color:#777;font-size:.78rem">👍{rr["l"]}·{rr["d"]}</span><br>{rr["t"]}</div>',unsafe_allow_html=True)
    st.caption(f"{pg}/{tp} 페이지")

with t2:
    st.markdown("### 📊 통계")
    m1,m2,m3,m4=st.columns(4)
    m1.metric("댓글수",f"{len(df)}");m2.metric("총좋아요",f"{df['좋아요'].sum():,}")
    m3.metric("평균좋아요",f"{df['좋아요'].mean():.1f}");m4.metric("평균글자",f"{df['글자수'].mean():.0f}")
    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        dc=df["작성일"].value_counts().sort_index()
        f1=px.area(x=dc.index,y=dc.values,labels={"x":"날짜","y":"수"},color_discrete_sequence=["#f7797d"])
        f1.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),title="📅 날짜별")
        st.plotly_chart(f1,use_container_width=True)
    with c2:
        f2=px.histogram(df,x="좋아요",nbins=30,color_discrete_sequence=["#FBD786"])
        f2.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),title="👍 좋아요분포")
        st.plotly_chart(f2,use_container_width=True)
    c3,c4=st.columns(2)
    with c3:
        f3=px.histogram(df,x="글자수",nbins=30,color_discrete_sequence=["#C6FFDD"])
        f3.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),title="✍️ 글자수분포")
        st.plotly_chart(f3,use_container_width=True)
    with c4:
        st.markdown("#### 🏆 좋아요 TOP10")
        tp10=df.nlargest(10,"좋아요")[["작성자","댓글","좋아요"]].reset_index(drop=True)
        tp10.index+=1;st.dataframe(tp10,use_container_width=True,height=350)

with t3:
    st.markdown("### 🔑 키워드")
    ks=kw(df["댓글"].tolist(),25)
    if ks:
        kd=pd.DataFrame(ks,columns=["키워드","빈도"])
        f4=px.bar(kd.iloc[::-1],x="빈도",y="키워드",orientation="h",color="빈도",color_continuous_scale="Sunset")
        f4.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),height=650,showlegend=False,title="TOP 25 키워드")
        st.plotly_chart(f4,use_container_width=True)
        st.dataframe(kd,use_container_width=True)

with t4:
    st.markdown("### 😊 감정분석")
    if ds and"감정"in df.columns:
        sc=df["감정"].value_counts()
        a,b=st.columns(2)
        with a:
            f5=px.pie(values=sc.values,names=sc.index,hole=.45,color_discrete_sequence=["#4CAF50","#FF5252","#666"])
            f5.update_traces(textinfo="label+percent",textfont_size=14)
            f5.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(f5,use_container_width=True)
        with b:
            for lb in sc.index:
                ct=sc[lb];pct=ct/len(df)*100
                cl="#4CAF50"if"긍정"in lb else"#FF5252"if"부정"in lb else"#666"
                st.markdown(f'<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:18px;'
                    f'margin-bottom:10px;border-left:5px solid {cl}">'
                    f'<b style="font-size:1.2rem">{lb}</b><br>'
                    f'<span style="font-size:1.7rem;font-weight:800;color:{cl}">{ct}개</span>'
                    f' <span style="color:#888">({pct:.1f}%)</span></div>',unsafe_allow_html=True)
        st.markdown("---")
        sl=df.groupby("감정")["좋아요"].mean().reset_index()
        f6=px.bar(sl,x="감정",y="좋아요",color="감정",color_discrete_sequence=["#4CAF50","#FF5252","#666"])
        f6.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),showlegend=False,title="감정별 평균좋아요")
        st.plotly_chart(f6,use_container_width=True)
    else:st.info("감정분석을 켜고 다시 수집하세요")

with t5:
    st.markdown("### 📥 다운로드")
    dl=df.drop(columns=["rps"],errors="ignore")
    csv=dl.to_csv(index=False,encoding="utf-8-sig")
    st.download_button("📥 CSV 다운로드",csv,f"comments_{v}.csv","text/csv",use_container_width=True)
    st.markdown("---")
    js=dl.to_json(orient="records",force_ascii=False,indent=2)
    st.download_button("📥 JSON 다운로드",js,f"comments_{v}.json","application/json",use_container_width=True)
    st.markdown("---")
    st.markdown("#### 📋 미리보기")
    st.dataframe(dl,use_container_width=True,height=400)
