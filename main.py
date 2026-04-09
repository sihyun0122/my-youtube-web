import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="유튜브 댓글 수집기",
    page_icon="🎬",
    layout="wide"
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #FF0000;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .comment-box {
        background-color: #f9f9f9;
        border-left: 4px solid #FF0000;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    .comment-author {
        font-weight: bold;
        color: #333;
        margin-bottom: 4px;
    }
    .comment-text {
        color: #555;
        line-height: 1.6;
    }
    .comment-meta {
        color: #999;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .stat-card {
        background: linear-gradient(135deg, #FF0000, #CC0000);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# YouTube API 키 가져오기
# ============================================================
def get_api_key():
    """Streamlit secrets 또는 사이드바 입력에서 API 키를 가져옵니다."""
    # 1순위: Streamlit secrets.toml
    try:
        api_key = st.secrets["YOUTUBE_API_KEY"]
        if api_key:
            return api_key
    except (KeyError, FileNotFoundError):
        pass

    # 2순위: 사이드바에서 직접 입력
    return None


# ============================================================
# 유튜브 영상 ID 추출 함수
# ============================================================
def extract_video_id(url):
    """다양한 유튜브 URL 형식에서 영상 ID를 추출합니다."""
    patterns = [
        # 일반 URL: https://www.youtube.com/watch?v=VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        # 짧은 URL: https://youtu.be/VIDEO_ID
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        # 임베드 URL: https://www.youtube.com/embed/VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        # 쇼츠 URL: https://www.youtube.com/shorts/VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        # 그냥 VIDEO_ID만 입력한 경우
        r'^([a-zA-Z0-9_-]{11})$',
    ]

    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)

    return None


# ============================================================
# 영상 정보 가져오기
# ============================================================
def get_video_info(youtube, video_id):
    """영상의 기본 정보를 가져옵니다."""
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        )
        response = request.execute()

        if response["items"]:
            item = response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]

            return {
                "title": snippet.get("title", "제목 없음"),
                "channel": snippet.get("channelTitle", "채널명 없음"),
                "published": snippet.get("publishedAt", "")[:10],
                "description": snippet.get("description", "")[:300],
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }
        return None

    except HttpError as e:
        st.error(f"영상 정보를 가져오는 중 오류: {e}")
        return None


# ============================================================
# 댓글 가져오기
# ============================================================
def get_comments(youtube, video_id, max_comments=100):
    """영상의 댓글을 가져옵니다."""
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                order="relevance",  # relevance(관련성) 또는 time(최신순)
                textFormat="plainText"
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "작성자": snippet.get("authorDisplayName", ""),
                    "댓글": snippet.get("textDisplay", ""),
                    "좋아요": snippet.get("likeCount", 0),
                    "작성일": snippet.get("publishedAt", "")[:10],
                    "수정일": snippet.get("updatedAt", "")[:10],
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return comments

    except HttpError as e:
        error_reason = e.error_details[0]["reason"] if e.error_details else str(e)
        if "commentsDisabled" in str(e):
            st.error("⚠️ 이 영상은 댓글이 비활성화되어 있습니다.")
        elif "forbidden" in str(e).lower():
            st.error("⚠️ API 키 권한 문제입니다. YouTube Data API v3가 활성화되어 있는지 확인하세요.")
        else:
            st.error(f"댓글을 가져오는 중 오류 발생: {error_reason}")
        return []


# ============================================================
# 메인 앱
# ============================================================
def main():
    st.markdown('<div class="main-header">🎬 유튜브 댓글 수집기</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">유튜브 영상 링크를 입력하면 댓글을 수집하여 보여줍니다</div>', unsafe_allow_html=True)

    # --- 사이드바 ---
    st.sidebar.title("⚙️ 설정")

    api_key = get_api_key()

    if not api_key:
        st.sidebar.warning("API 키가 secrets에 설정되지 않았습니다. 아래에 직접 입력하세요.")
        api_key = st.sidebar.text_input(
            "YouTube Data API v3 키",
            type="password",
            help="Google Cloud Console에서 발급받은 API 키를 입력하세요."
        )

    if api_key:
        st.sidebar.success("✅ API 키가 설정되었습니다.")
    else:
        st.sidebar.info("API 키를 입력해주세요.")

    st.sidebar.markdown("---")

    max_comments = st.sidebar.slider(
        "수집할 최대 댓글 수",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="댓글 수가 많을수록 시간이 오래 걸립니다."
    )

    sort_option = st.sidebar.radio(
        "댓글 정렬",
        ["좋아요 많은 순", "최신순", "오래된 순"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📖 사용법
    1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
    2. YouTube Data API v3 활성화
    3. API 키 발급
    4. 유튜브 영상 링크 입력
    5. 댓글 수집!
    """)

    # --- 메인 영역 ---
    st.markdown("---")

    url = st.text_input(
        "🔗 유튜브 영상 링크를 입력하세요",
        placeholder="https://www.youtube.com/watch?v=...",
        help="일반 링크, 짧은 링크(youtu.be), 쇼츠 링크 모두 지원합니다."
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        search_clicked = st.button("🔍 댓글 수집하기", use_container_width=True, type="primary")

    if search_clicked:
        # 유효성 검사
        if not api_key:
            st.error("❌ API 키를 먼저 입력해주세요!")
            return

        if not url:
            st.error("❌ 유튜브 링크를 입력해주세요!")
            return

        video_id = extract_video_id(url)
        if not video_id:
            st.error("❌ 올바른 유튜브 링크가 아닙니다. 다시 확인해주세요!")
            return

        # YouTube API 클라이언트 생성
        try:
            youtube = build("youtube", "v3", developerKey=api_key)
        except Exception as e:
            st.error(f"❌ API 연결 실패: {e}")
            return

        # --- 영상 정보 가져오기 ---
        with st.spinner("📡 영상 정보를 가져오는 중..."):
            video_info = get_video_info(youtube, video_id)

        if not video_info:
            st.error("❌ 영상 정보를 가져올 수 없습니다. 링크를 다시 확인해주세요.")
            return

        # 영상 정보 표시
        st.markdown("---")
        st.subheader("📺 영상 정보")

        info_col1, info_col2 = st.columns([1, 2])

        with info_col1:
            if video_info["thumbnail"]:
                st.image(video_info["thumbnail"], use_container_width=True)

        with info_col2:
            st.markdown(f"### {video_info['title']}")
            st.markdown(f"**채널:** {video_info['channel']}")
            st.markdown(f"**게시일:** {video_info['published']}")

            stat_col1, stat_col2, stat_col3 = st.columns(3)
            with stat_col1:
                st.metric("👀 조회수", f"{video_info['view_count']:,}")
            with stat_col2:
                st.metric("👍 좋아요", f"{video_info['like_count']:,}")
            with stat_col3:
                st.metric("💬 댓글수", f"{video_info['comment_count']:,}")

        # --- 댓글 가져오기 ---
        st.markdown("---")
        st.subheader("💬 댓글 목록")

        with st.spinner(f"💬 댓글을 수집하는 중... (최대 {max_comments}개)"):
            comments = get_comments(youtube, video_id, max_comments)

        if not comments:
            st.warning("수집된 댓글이 없습니다.")
            return

        # DataFrame 생성
        df = pd.DataFrame(comments)

        # 정렬
        if sort_option == "좋아요 많은 순":
            df = df.sort_values(by="좋아요", ascending=False).reset_index(drop=True)
        elif sort_option == "최신순":
            df = df.sort_values(by="작성일", ascending=False).reset_index(drop=True)
        elif sort_option == "오래된 순":
            df = df.sort_values(by="작성일", ascending=True).reset_index(drop=True)

        # 수집 결과 요약
        st.success(f"✅ 총 **{len(df)}개**의 댓글을 수집했습니다!")

        # 탭으로 보기 방식 나누기
        tab1, tab2 = st.tabs(["📋 카드 보기", "📊 테이블 보기"])

        with tab1:
            # 검색 필터
            search_keyword = st.text_input("🔎 댓글 내 키워드 검색", placeholder="검색어를 입력하세요...")

            if search_keyword:
                filtered_df = df[df["댓글"].str.contains(search_keyword, case=False, na=False)]
                st.info(f"'{search_keyword}' 검색 결과: {len(filtered_df)}개")
            else:
                filtered_df = df

            # 댓글 카드 형태로 표시
            for idx, row in filtered_df.iterrows():
                st.markdown(f"""
                <div class="comment-box">
                    <div class="comment-author">👤 {row['작성자']}</div>
                    <div class="comment-text">{row['댓글']}</div>
                    <div class="comment-meta">👍 {row['좋아요']}  |  📅 {row['작성일']}</div>
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            st.dataframe(
                df,
                use_container_width=True,
                height=500,
                column_config={
                    "좋아요": st.column_config.NumberColumn("👍 좋아요", format="%d"),
                    "작성자": st.column_config.TextColumn("👤 작성자", width="medium"),
                    "댓글": st.column_config.TextColumn("💬 댓글", width="large"),
                    "작성일": st.column_config.TextColumn("📅 작성일", width="small"),
                }
            )

        # --- CSV 다운로드 ---
        st.markdown("---")

        csv_data = df.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            label="📥 CSV 파일로 다운로드",
            data=csv_data,
            file_name=f"youtube_comments_{video_id}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    main()
