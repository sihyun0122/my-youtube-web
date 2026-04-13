import streamlit as st
import pandas as pd
import re
import plotly.express as px
from collections import Counter
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(page_title="YT댓글분석기",page_icon="🎬",layout="wide")
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
.FIRE{background:linear-gradient(135deg,#ff9a9e,#fad0c4,#ffd1ff);border-radius:20px;
padding:22px;margin-bottom:14px;border:2px solid rgba(255,255,255,.15);color:#000}
.FIRE b{color:#c62828}.FIRE span{color:#555}
.RANK{background:rgba(255,255,255,.05);border-radius:14px;padding:14px;margin-bottom:8px;
border-left:4px solid #FBD786}
.HL{background:rgba(255,215,0,.15);border:1px solid rgba(255,215,0,.3);border-radius:8px;padding:2px 8px}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a0a1a,#1a1a3e)}
section[data-testid="stSidebar"] *{color:#ccc!important}
div[data-testid="stMetric"]{background:rgba(255,255,255,.05);border-radius:14px;padding:12px}
div[data-testid="stMetric"] label{color:#aaa!important}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#fff!important;font-weight:700}
.stTabs [data-baseweb="tab"]{color:#ccc;font-weight:600}
.stTabs [aria-selected="true"]{color:#FBD786!important;border-color:#f7797d!important}
</style>""",unsafe_allow_html=True)

def api_key():
    try:return st.secrets["YOUTUBE_API_KEY"]
    except:return None

def vid_id(u):
    for p in[r'v=([a-zA-Z0-9_-]{11})',r'youtu\.be/([a-zA-Z0-9_-]{11})',
             r'shorts/([a-zA-Z0-9_-]{11})',r'embed/([a-zA-Z0-9_-]{11})',
             r'^([a-zA-Z0-9_-]{11})$']:
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
                d=s.get("publishedAt","")[:10],
                img=s["thumbnails"].get("high",{}).get("url",""),
                vc=int(t.get("viewCount",0)),lc=int(t.get("likeCount",0)),
                cc=int(t.get("commentCount",0)))
    except:pass
    return None

def fetch(yt,v,mx=200,od="relevance"):
    out,tk=[],None
    try:
        while len(out)<mx:
            r=yt.commentThreads().list(
                part="snippet,replies",videoId=v,
                maxResults=min(100,mx-len(out)),
                pageToken=tk,order=od,textFormat="plainText").execute()
            for i in r.get("items",[]):
                sn=i["snippet"]["topLevelComment"]["snippet"]
                rc=i["snippet"].get("totalReplyCount",0)
                rps=[]
                if rc>0 and i.get("replies"):
                    for rr in i["replies"]["comments"]:
                        rs=rr["snippet"]
                        rps.append(dict(a=rs.get("authorDisplayName",""),
                            t=rs.get("textDisplay",""),
                            l=rs.get("likeCount",0),
                            d=rs.get("publishedAt","")[:10]))
                raw=sn.get("publishedAt","")
                out.append(dict(작성자=sn.get("authorDisplayName",""),
                    댓글=sn.get("textDisplay",""),좋아요=sn.get("likeCount",0),
                    작성일=raw[:10],시간=raw[11:13]if len(raw)>13 else"00",
                    대댓글수=rc,rps=rps,글자수=len(sn.get("textDisplay",""))))
            tk=r.get("nextPageToken")
            if not tk:break
        return out
    except HttpError as e:
        if "commentsDisabled" in str(e):st.error("댓글 비활성화 영상")
        else:st.error(f"오류:{e}")
        return[]

def senti(t):
    lo=t.lower()
    p=sum(1 for w in['좋아','최고','대박','감동','사랑','멋지','재밌','행복','감사',
        '응원','ㅋㅋ','ㅎㅎ','귀엽','짱','레전드','인정','완벽','good','great',
        'love','amazing','awesome','best','nice','fantastic','힐링','축하']if w in lo)
    n=sum(1 for w in['싫어','최악','별로','실망','짜증','화나','슬프','쓰레기',
        '노잼','답답','혐오','bad','worst','hate','terrible','boring','awful']if w in lo)
    if p>n:return"긍정 😊"
    if n>p:return"부정 😞"
    return"중립 😐"

def scls(s):
    if"긍정"in s:return"P"
    if"부정"in s:return"N"
    return"U"

def kwext(texts,n=25):
    st_=set("그 저 이 것 수 를 에 의 가 은 는 도 와 다 한 하 있 없 않 더 때 되 로 해 들 좀 너무 진짜 정말 제 내 나 거 게 같 인데 이거 그냥 아 네 왜 뭐 또 안 잘 못 합니다 하는 저는 나는 근데 이건 the a an is are to of and in that it for on with was be this".split())
    ws=re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}'," ".join(texts))
    return Counter([w.lower()for w in ws if w.lower()not in st_]).most_common(n)

def ctype(t):
    if re.search(r'[?？]|뭐에요|인가요|일까|어떻게|알려|궁금',t):return"❓ 질문형"
    if re.search(r'ㅋ{2,}|ㅎ{2,}|😂|🤣|ㅋㅋ',t):return"😂 유머형"
    if re.search(r'[😭😢💔]|ㅠ{2,}|슬프|울|감동|눈물',t):return"😢 감성형"
    if len(t)>100:return"📝 장문형"
    return"💬 일반형"

def ai_summary(df):
    n=len(df)
    if n==0:return"댓글 없음"
    parts=[]
    if"감정"in df.columns:
        pc=len(df[df["감정"].str.contains("긍정")])
        nc=len(df[df["감정"].str.contains("부정")])
        parts.append(f"📊 총 {n}개 중 긍정 {pc}개({pc/n*100:.0f}%), 부정 {nc}개({nc/n*100:.0f}%)")
        if pc>nc*2:parts.append("🎉 매우 긍정적 반응!")
        elif nc>pc:parts.append("⚠️ 부정 반응 많음")
        else:parts.append("⚖️ 긍정/부정 비슷")
    top=df.nlargest(1,"좋아요").iloc[0]
    parts.append(f"🏆 인기댓글(👍{top['좋아요']}): \"{top['댓글'][:50]}...\"")
    ks=kwext(df["댓글"].tolist(),5)
    if ks:parts.append(f"🔑 핵심: {', '.join([w[0]for w in ks])}")
    return"\n\n".join(parts)

# ── 사이드바 ──
with st.sidebar:
    st.markdown("## ⚙️ 설정")
    st.markdown("---")
    key=api_key()
    if not key:key=st.text_input("🔑 API Key",type="password",placeholder="API키...")
    if key:st.success("✅ 연결")
    else:st.warning("API키 필요")
    st.markdown("---")
    mx=st.slider("최대 댓글",10,500,150,10)
    od=st.radio("정렬",["관련성","최신"])
    om={"관련성":"relevance","최신":"time"}
    dr=st.checkbox("대댓글",True)
    ds=st.checkbox("감정분석",True)
    st.markdown("---")
    st.markdown("### 🎯 키워드 알림")
    alert_kw=st.text_input("하이라이트",placeholder="예: 가격")
    st.markdown("---")
    with st.expander("📖 API키 발급"):
        st.markdown("1.[Google Cloud Console](https://console.cloud.google.com)\n2.프로젝트생성\n3.YouTube Data API v3 활성화\n4.API키 생성")

# ── 헤더 ──
st.markdown('<p class="T">🎬 YouTube 댓글 분석기</p>',unsafe_allow_html=True)
st.markdown('<p class="S">댓글수집 · 감정분석 · 키워드 · 랭킹 · 시간대 · 유형분류 · 비교</p>',unsafe_allow_html=True)
st.markdown('<div class="D"></div>',unsafe_allow_html=True)

mode=st.radio("모드",["🎬 단일분석","⚔️ 비교분석"],horizontal=True,label_visibility="collapsed")

if mode=="🎬 단일분석":
    c1,c2=st.columns([5,1])
    with c1:url=st.text_input("u",placeholder="유튜브 링크 🔗",label_visibility="collapsed",key="u1")
    with c2:gobtn=st.button("🚀 분석",type="primary",use_container_width=True)
    urls=[url]if gobtn else[]
else:
    c1,c2,c3=st.columns([2,2,1])
    with c1:url1=st.text_input("영상1",placeholder="첫번째 링크 🔗",label_visibility="collapsed",key="u1")
    with c2:url2=st.text_input("영상2",placeholder="두번째 링크 🔗",label_visibility="collapsed",key="u2")
    with c3:gobtn=st.button("⚔️ 비교",type="primary",use_container_width=True)
    urls=[url1,url2]if gobtn else[]

if urls:
    if not key:st.error("❌ API키!");st.stop()
    try:yt=build("youtube","v3",developerKey=key)
    except Exception as e:st.error(f"연결실패:{e}");st.stop()
    results=[]
    for i,u in enumerate(urls):
        if not u:st.error(f"❌ 링크{i+1}!");st.stop()
        v=vid_id(u)
        if not v:st.error(f"❌ 잘못된 링크{i+1}!");st.stop()
        with st.spinner(f"📡 영상{i+1}..."):vi=vinfo(yt,v)
        if not vi:st.error(f"영상{i+1} 없음");st.stop()
        with st.spinner(f"💬 댓글{i+1}({mx}개)..."):cm=fetch(yt,v,mx,om[od])
        if not cm:st.stop()
        d=pd.DataFrame(cm)
        if ds:d["감정"]=d["댓글"].apply(senti)
        d["유형"]=d["댓글"].apply(ctype)
        results.append(dict(df=d,vi=vi,v=v))
    st.session_state.update(results=results,mode=mode,ds=ds,dr=dr,alert_kw=alert_kw)

if "results" not in st.session_state:
    st.markdown("""<div class="G" style="text-align:center;padding:80px 20px">
    <p style="font-size:4rem;margin:0">🎬</p>
    <p style="font-size:1.4rem;font-weight:700;color:#fff">유튜브 링크를 입력하세요</p>
    <p style="color:#888">단일분석 또는 두 영상 비교</p></div>""",unsafe_allow_html=True)
    st.stop()

res=st.session_state["results"]
md=st.session_state["mode"]
ds=st.session_state.get("ds",True)
dr=st.session_state.get("dr",True)
alert_kw=st.session_state.get("alert_kw","")
df=res[0]["df"];vi=res[0]["vi"];v=res[0]["v"]

# ── 영상정보 ──
st.markdown('<div class="D"></div>',unsafe_allow_html=True)
for idx,r in enumerate(res):
    _v,_d=r["vi"],r["df"]
    if len(res)>1:st.markdown(f"### {'🔴' if idx==0 else '🔵'} 영상{idx+1}")
    a,b=st.columns([1,2])
    with a:
        if _v["img"]:st.image(_v["img"],use_container_width=True)
    with b:
        st.markdown(f"### 🎬 {_v['t']}")
        st.markdown(f"📺 **{_v['ch']}** · 📅 {_v['d']}")
        x1,x2,x3,x4=st.columns(4)
        x1.markdown(f'<div class="B B1"><div class="BL">👀 조회</div><div class="BN">{fm(_v["vc"])}</div></div>',unsafe_allow_html=True)
        x2.markdown(f'<div class="B B2"><div class="BL">👍 좋아요</div><div class="BN">{fm(_v["lc"])}</div></div>',unsafe_allow_html=True)
        x3.markdown(f'<div class="B B3"><div class="BL">💬 댓글</div><div class="BN">{fm(_v["cc"])}</div></div>',unsafe_allow_html=True)
        eg=(_v["cc"]/_v["vc"]*100)if _v["vc"]>0 else 0
        x4.markdown(f'<div class="B B4"><div class="BL">📈 참여</div><div class="BN">{eg:.2f}%</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="D"></div>',unsafe_allow_html=True)

st.success(f"✅ **{len(df)}개** 댓글 수집완료!")

# ═══ 탭 ═══
tab_names=["💬댓글","🔥인기","🏅랭킹","📊통계","⏰시간","🔑키워드","😊감정","📏유형","📥저장"]
if md!="🎬 단일분석":tab_names.append("⚔️비교")
tabs=st.tabs(tab_names)

with tabs[0]:
    f1,f2,f3=st.columns([2,1,1])
    with f1:q=st.text_input("🔎",placeholder="검색...",key="q")
    with f2:so=st.selectbox("정렬",["좋아요순","최신순","오래된순","긴순"])
    with f3:
        sf="전체"
        if ds and"감정"in df.columns:sf=st.selectbox("감정",["전체","긍정 😊","부정 😞","중립 😐"])
    fd=df.copy()
    if q:fd=fd[fd["댓글"].str.contains(q,case=False,na=False)]
    if sf!="전체"and"감정"in fd.columns:fd=fd[fd["감정"]==sf]
    sm={"좋아요순":("좋아요",False),"최신순":("작성일",False),"오래된순":("작성일",True),"긴순":("글자수",False)}
    co,ac=sm[so];fd=fd.sort_values(co,ascending=ac).reset_index(drop=True)
    st.info(f"**{len(fd)}개**")
    pp=20;tp=max(1,(len(fd)-1)//pp+1)
    pg=st.number_input("페이지",1,tp,1,key="pg")
    si,ei=(pg-1)*pp,min(pg*pp,len(fd))
    for _,row in fd.iloc[si:ei].iterrows():
        sh=""
        if ds and"감정"in df.columns:sh=f' <span class="{scls(row["감정"])}">{row["감정"]}</span>'
        lk=f'<span class="LK">👍{row["좋아요"]}</span> 'if row["좋아요"]>0 else""
        rp=f' · 💬{row["대댓글수"]}'if row["대댓글수"]>0 else""
        txt=row["댓글"]
        if alert_kw and alert_kw in txt:
            txt=txt.replace(alert_kw,f'<span class="HL">{alert_kw}</span>')
        st.markdown(f'<div class="C"><b>👤{row["작성자"]}</b>{sh} <span style="font-size:.7rem;color:#888">{row["유형"]}</span><br><span style="color:#ccc;line-height:1.8">{txt}</span><br><span style="font-size:.78rem;color:#888">{lk}📅{row["작성일"]}{rp}</span></div>',unsafe_allow_html=True)
        if dr and row["대댓글수"]>0 and row["rps"]:
            for rr in row["rps"]:
                st.markdown(f'<div class="R">↳<b>{rr["a"]}</b> <span style="color:#777;font-size:.78rem">👍{rr["l"]}·{rr["d"]}</span><br>{rr["t"]}</div>',unsafe_allow_html=True)
    st.caption(f"{pg}/{tp}")

with tabs[1]:
    st.markdown("### 🔥 인기 TOP3")
    top3=df.nlargest(3,"좋아요")
    for i,(_,row) in enumerate(top3.iterrows()):
        md_=["🥇","🥈","🥉"][i]
        st.markdown(f'<div class="FIRE"><b>{md_} {row["작성자"]}</b> <span>👍{row["좋아요"]}</span><br><br><span style="font-size:1.05rem">{row["댓글"]}</span><br><br><span style="font-size:.8rem">📅{row["작성일"]}</span></div>',unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 💡 AI 요약")
    st.markdown(f'<div class="G" style="white-space:pre-line">{ai_summary(df)}</div>',unsafe_allow_html=True)

with tabs[2]:
    st.markdown("### 🏅 댓글러 랭킹")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("#### 📝 다댓글왕")
        cnt=df["작성자"].value_counts().head(10)
        for i,(name,num) in enumerate(cnt.items()):
            md_="🥇"if i==0 else"🥈"if i==1 else"🥉"if i==2 else f"{i+1}."
            st.markdown(f'<div class="RANK">{md_} <b>{name}</b> — {num}개</div>',unsafe_allow_html=True)
    with c2:
        st.markdown("#### 👍 좋아요왕")
        ls=df.groupby("작성자")["좋아요"].sum().nlargest(10)
        for i,(name,num) in enumerate(ls.items()):
            md_="🥇"if i==0 else"🥈"if i==1 else"🥉"if i==2 else f"{i+1}."
            st.markdown(f'<div class="RANK">{md_} <b>{name}</b> — 👍{num}</div>',unsafe_allow_html=True)

with tabs[3]:
    st.markdown("### 📊 통계")
    m1,m2,m3,m4=st.columns(4)
    m1.metric("댓글",f"{len(df)}")
    m2.metric("총좋아요",f"{df['좋아요'].sum():,}")
    m3.metric("평균좋아요",f"{df['좋아요'].mean():.1f}")
    m4.metric("평균글자",f"{df['글자수'].mean():.0f}")
    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        dc=df["작성일"].value_counts().sort_index()
        fg=px.area(x=dc.index,y=dc.values,labels={"x":"날짜","y":"수"},color_discrete_sequence=["#f7797d"])
        fg.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),title="📅 날짜별")
        st.plotly_chart(fg,use_container_width=True)
    with c2:
        fg2=px.histogram(df,x="좋아요",nbins=30,color_discrete_sequence=["#FBD786"])
        fg2.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),title="👍 분포")
        st.plotly_chart(fg2,use_container_width=True)

with tabs[4]:
    st.markdown("### ⏰ 시간대별")
    hr=df["시간"].value_counts().reindex([f"{i:02d}"for i in range(24)],fill_value=0)
    fg3=px.bar(x=hr.index,y=hr.values,labels={"x":"시(UTC)","y":"수"},color=hr.values,color_continuous_scale="Sunset")
    fg3.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),showlegend=False)
    st.plotly_chart(fg3,use_container_width=True)
    st.info(f"🔥 피크: UTC **{hr.idxmax()}시** ({int(hr.max())}개)")

with tabs[5]:
    st.markdown("### 🔑 키워드 TOP25")
    ks=kwext(df["댓글"].tolist(),25)
    if ks:
        kd=pd.DataFrame(ks,columns=["키워드","빈도"])
        fg4=px.bar(kd.iloc[::-1],x="빈도",y="키워드",orientation="h",color="빈도",color_continuous_scale="Sunset")
        fg4.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10),height=650,showlegend=False)
        st.plotly_chart(fg4,use_container_width=True)

with tabs[6]:
    st.markdown("### 😊 감정")
    if ds and"감정"in df.columns:
        sc=df["감정"].value_counts()
        a,b=st.columns(2)
        with a:
            fg5=px.pie(values=sc.values,names=sc.index,hole=.45,color_discrete_sequence=["#4CAF50","#FF5252","#666"])
            fg5.update_traces(textinfo="label+percent",textfont_size=14)
            fg5.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fg5,use_container_width=True)
        with b:
            for lb in sc.index:
                ct=sc[lb];pct=ct/len(df)*100
                cl="#4CAF50"if"긍정"in lb else"#FF5252"if"부정"in lb else"#666"
                st.markdown(f'<div style="background:rgba(255,255,255,.06);border-radius:14px;padding:18px;margin-bottom:10px;border-left:5px solid {cl}"><b style="font-size:1.2rem">{lb}</b><br><span style="font-size:1.7rem;font-weight:800;color:{cl}">{ct}개</span> <span style="color:#888">({pct:.1f}%)</span></div>',unsafe_allow_html=True)
    else:st.info("감정분석 켜세요")

with tabs[7]:
    st.markdown("### 📏 유형분류")
    tc=df["유형"].value_counts()
    fg6=px.pie(values=tc.values,names=tc.index,hole=.4,color_discrete_sequence=px.colors.qualitative.Pastel)
    fg6.update_traces(textinfo="label+percent",textfont_size=13)
    fg6.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=40,b=10))
    st.plotly_chart(fg6,use_container_width=True)
    for tn in tc.index:
        with st.expander(f"{tn} ({tc[tn]}개)"):
            for _,r in df[df["유형"]==tn].head(5).iterrows():
                st.markdown(f"**{r['작성자']}**: {r['댓글'][:100]}")

with tabs[8]:
    st.markdown("### 📥 다운로드")
    dl=df.drop(columns=["rps"],errors="ignore")
    st.download_button("📥 CSV",dl.to_csv(index=False,encoding="utf-8-sig"),f"comments_{v}.csv","text/csv",use_container_width=True)
    st.markdown("---")
    st.download_button("📥 JSON",dl.to_json(orient="records",force_ascii=False,indent=2),f"comments_{v}.json","application/json",use_container_width=True)
    st.markdown("---")
    st.dataframe(dl,use_container_width=True,height=400)

if md!="🎬 단일분석" and len(res)==2 and len(tabs)>9:
    with tabs[9]:
        st.markdown("### ⚔️ 비교")
        d1,d2=res[0]["df"],res[1]["df"]
        rows=[("댓글수",len(d1),len(d2)),
              ("평균좋아요",round(d1["좋아요"].mean(),1),round(d2["좋아요"].mean(),1)),
              ("평균글자",round(d1["글자수"].mean(),1),round(d2["글자수"].mean(),1))]
        if ds:
            p1=round(len(d1[d1["감정"].str.contains("긍정")])/len(d1)*100,1)
            p2=round(len(d2[d2["감정"].str.contains("긍정")])/len(d2)*100,1)
            rows.append(("긍정%",p1,p2))
        comp=pd.DataFrame(rows,columns=["항목","🔴영상1","🔵영상2"])
        st.dataframe(comp,use_container_width=True)
        cm=comp.melt(id_vars="항목",var_name="영상",value_name="값")
        fg7=px.bar(cm,x="항목",y="값",color="영상",barmode="group",color_discrete_map={"🔴영상1":"#f7797d","🔵영상2":"#4facfe"})
        fg7.update_layout(template="plotly_dark",plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fg7,use_container_width=True)
