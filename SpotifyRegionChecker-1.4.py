from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from collections import defaultdict
import time
import os
import logging
from logging.handlers import RotatingFileHandler
import sys

# ==== 日志系统设置 ==== #
logger = logging.getLogger("SpotifyRegionChecker")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
if not logger.hasHandlers():
    file_handler = RotatingFileHandler('spotify_app.log', maxBytes=3*1024*1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
logger.info("✅ 程序已启动，日志系统初始化成功")

# ==== Spotify API 授权 ==== #
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    st.error("错误：缺少Spotify API凭证。请检查环境变量配置。")
    logger.error("❌ 缺少Spotify API凭证，程序终止 [Type: Config]")
    st.stop()
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# ==== 大洲国家定义 ==== #
CONTINENT_COUNTRIES = {
    "亚洲": [("CN", "中国"), ("TW", "台湾"), ("HK", "香港"),
             ("JP", "日本"), ("SG", "新加坡"),
             ("TH", "泰国"), ("VN", "越南"), ("ID", "印尼")],
    "欧洲": [("GB", "英国"), ("FR", "法国"), ("DE", "德国"),
             ("ES", "西班牙"), ("NL", "荷兰"), ("SE", "瑞典"),
             ("BE", "比利时")],
    "北美洲": [("US", "美国"), ("CA", "加拿大"), ("MX", "墨西哥")],
    "南美洲": [("BR", "巴西"), ("AR", "阿根廷"), ("CL", "智利"),
             ("CO", "哥伦比亚"), ("PE", "秘鲁")],
    "大洋洲": [("AU", "澳大利亚"), ("NZ", "新西兰")],
    "非洲": [("ZA", "南非"), ("EG", "埃及"), ("NG", "尼日利亚")]
}
CONTINENT_COUNTRIES_EN = {
    "Asia": [("CN", "China"), ("TW", "Taiwan"), ("HK", "Hong Kong"),
             ("JP", "Japan"), ("SG", "Singapore"),
             ("TH", "Thailand"), ("VN", "Vietnam"), ("ID", "Indonesia")],
    "Europe": [("GB", "United Kingdom"), ("FR", "France"), ("DE", "Germany"),
               ("ES", "Spain"), ("NL", "Netherlands"), ("SE", "Sweden"),
               ("BE", "Belgium")],
    "North America": [("US", "United States"), ("CA", "Canada"), ("MX", "Mexico")],
    "South America": [("BR", "Brazil"), ("AR", "Argentina"), ("CL", "Chile"),
                      ("CO", "Colombia"), ("PE", "Peru")],
    "Oceania": [("AU", "Australia"), ("NZ", "New Zealand")],
    "Africa": [("ZA", "South Africa"), ("EG", "Egypt"), ("NG", "Nigeria")]
}

# ==== 语言包 ==== #
TRANSLATIONS = {
    "zh": {
        "title": "Spotify 专辑地区查询",
        "search_tab": "🔍 专辑/艺人搜索",
        "album_link_tab": "🔗 专辑直链",
        "search_placeholder": "输入专辑/艺人名",
        "search_btn": "🔍 搜索",
        "artist_section": "👤 艺人",
        "album_section": "💿 专辑",
        "view_albums": "查看专辑",
        "view_region": "查看地区分布",
        "album_url_placeholder": "例如：https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "query_btn": "➡️ 查询",
        "usage_title": "💡 使用说明",
        "usage_content": """
- 支持输入专辑/艺人名进行模糊搜索，或直接粘贴专辑链接查全球可用地区。
- 可查看艺人全部专辑，点击任一专辑实时显示地区分布。
- 各大洲代表性国家、专辑基础信息与曲目列表一目了然。
- 数据由 Spotify 官方接口实时查询，仅供学习与非商业用途。
""",
        "artist_albums_title": "🎤 艺人全部专辑",
        "no_artist_album": "该艺人无专辑数据。",
        "loading_album": "📡 正在获取专辑信息 ...",
        "loading_track": "🎶 正在加载曲目和地区数据 ...",
        "loading_time": "⏱️ 查询耗时: {time:.2f} 秒",
        "track_list_title": "🎵 曲目列表",
        "sort_track": "排序方式",
        "sort_order": "曲目顺序",
        "sort_popularity": "流行度",
        "region_dist_title": "🌍 可用地区分布（共{total}地区）",
        "region_dist_caption": "以下仅显示代表性国家，灰色为未上架。",
        "no_markets": "⚠️ 此专辑的地区信息不可用，可能为新专辑或特殊版权。",
        "error_fetch": "❌ 获取专辑信息失败，请稍后重试或检查链接。",
        "artist": "艺术家",
        "release_date": "发行日期",
        "album_type": "专辑类型",
        "popularity": "流行度",
        "genres": "流派",
        "followers": "关注者",
        "artist_link": "艺术家链接",
        "search_no_result": "未找到相关专辑或艺人，请换个关键词试试。",
        "powered": "🚀 Powered by Spotify | 纯学习展示用途 | 设计美化：二千",
        "language": "语言 / Language"
    },
    "en": {
        "title": "Spotify Album Region Checker",
        "search_tab": "🔍 Album/Artist Search",
        "album_link_tab": "🔗 Album Link",
        "search_placeholder": "Enter album/artist name",
        "search_btn": "🔍 Search",
        "artist_section": "👤 Artists",
        "album_section": "💿 Albums",
        "view_albums": "View Albums",
        "view_region": "View Regions",
        "album_url_placeholder": "E.g. https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "query_btn": "➡️ Check",
        "usage_title": "💡 Usage Guide",
        "usage_content": """
- Supports fuzzy search for album/artist names or paste album link to check region availability.
- View all albums of an artist and check region coverage for any album in real time.
- Visualizes coverage for major countries, album info, and track list at a glance.
- Data from Spotify API, for learning/non-commercial use only.
""",
        "artist_albums_title": "🎤 All Albums of Artist",
        "no_artist_album": "No album data for this artist.",
        "loading_album": "📡 Loading album info ...",
        "loading_track": "🎶 Loading tracks and regions ...",
        "loading_time": "⏱️ Time: {time:.2f} s",
        "track_list_title": "🎵 Track List",
        "sort_track": "Sort Tracks By",
        "sort_order": "Track Order",
        "sort_popularity": "Popularity",
        "region_dist_title": "🌍 Region Coverage ({total} regions)",
        "region_dist_caption": "Only major countries shown below, gray means unavailable.",
        "no_markets": "⚠️ Region info unavailable, may be new or restricted album.",
        "error_fetch": "❌ Failed to fetch album info. Please retry or check link.",
        "artist": "Artist",
        "release_date": "Release Date",
        "album_type": "Album Type",
        "popularity": "Popularity",
        "genres": "Genres",
        "followers": "Followers",
        "artist_link": "Artist Link",
        "search_no_result": "No matching albums/artists found. Try another keyword.",
        "powered": "🚀 Powered by Spotify | For demo only | UI: 二千",
        "language": "语言 / Language"
    }
}

def extract_album_id(url):
    if not url or not isinstance(url, str):
        return None
    pattern = r"(?:spotify\.com/album/|:album:)([\w\d]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@st.cache_data(ttl=3600, show_spinner=False)
def get_album_data(album_id):
    if not album_id or not isinstance(album_id, str):
        logger.warning("无效专辑ID [Type: Input]")
        raise ValueError("无效的专辑ID")
    retries = 2
    for attempt in range(retries + 1):
        try:
            start_time = time.time()
            album = sp.album(album_id)
            elapsed = time.time() - start_time
            logger.info(f"Fetched album {album_id} in {elapsed:.2f}s [Type: API]")
            if not album.get('available_markets'):
                tracks = sp.album_tracks(album_id, limit=1)
                if tracks['items']:
                    track = sp.track(tracks['items'][0]['id'])
                    album['available_markets'] = track.get('available_markets', [])
            tracks = sp.album_tracks(album_id)
            album['tracks'] = tracks['items']
            track_ids = [track['id'] for track in album['tracks'] if track['id']]
            if track_ids:
                track_details = sp.tracks(track_ids)
                for i, track in enumerate(album['tracks']):
                    if i < len(track_details['tracks']):
                        track['popularity'] = track_details['tracks'][i].get('popularity', 0)
                        track['preview_url'] = track_details['tracks'][i].get('preview_url', None)
                        track['artists'] = track_details['tracks'][i].get('artists', [])
            album['genres'] = []
            album['artist_followers'] = 0
            album['artist_url'] = ''
            if album['artists']:
                artist = sp.artist(album['artists'][0]['id'])
                album['genres'] = artist.get('genres', [])
                album['artist_followers'] = artist.get('followers', {}).get('total', 0)
                album['artist_url'] = artist.get('external_urls', {}).get('spotify', '')
            logger.info(f"Successfully fetched album data for ID: {album_id} [Type: API]")
            return album
        except spotipy.SpotifyException as e:
            if hasattr(e, "http_status") and e.http_status == 429 and attempt < retries:
                retry_after = int(getattr(e, "headers", {}).get('Retry-After', 2))
                logger.warning(f"Rate limit hit for album {album_id}, retry after {retry_after}s [Type: API]")
                time.sleep(retry_after)
                continue
            logger.error(f"Spotify API error for album {album_id}: {str(e)} [Type: API]", exc_info=True)
            raise Exception("Spotify API错误")
        except Exception as e:
            logger.error(f"Failed to fetch album data for {album_id}: {str(e)} [Type: General]", exc_info=True)
            raise Exception("获取专辑数据失败")

@st.cache_data(ttl=3600, show_spinner=False)
def search_albums(query, limit=10):
    if not query or not isinstance(query, str):
        logger.warning("无效的搜索关键词 [Type: Input]")
        return [], []
    retries = 2
    albums, artists = [], []
    for attempt in range(retries + 1):
        try:
            album_results = sp.search(q=query, type='album', limit=limit)
            artist_results = sp.search(q=query, type='artist', limit=limit)
            albums = album_results['albums']['items']
            artists = artist_results['artists']['items']
            logger.info(f"Search successful for query: {query} [Type: API]")
            return albums, artists
        except spotipy.SpotifyException as e:
            if hasattr(e, "http_status") and e.http_status == 429 and attempt < retries:
                retry_after = int(getattr(e, "headers", {}).get('Retry-After', 2))
                logger.warning(f"Rate limit hit for search {query}, retry after {retry_after}s [Type: API]")
                time.sleep(retry_after)
                continue
            logger.error(f"Spotify API error for search {query}: {str(e)} [Type: API]", exc_info=True)
            raise Exception("Spotify API错误")
        except Exception as e:
            logger.error(f"Search failed for {query}: {str(e)} [Type: General]", exc_info=True)
            return [], []

def get_artist_albums(artist_id):
    albums = []
    seen = set()
    results = sp.artist_albums(artist_id=artist_id, album_type="album,single", limit=50)
    for item in results['items']:
        if item['id'] not in seen:
            albums.append(item)
            seen.add(item['id'])
    return albums

# ========= Streamlit 主体 ========= #

def main():
    st.set_page_config(page_title="Spotify 专辑地区查询", page_icon="🎵", layout="centered")
    st.markdown("""
      <style>
html, body, [class*="css"]  {
    background-color: #f7f7fa !important;
    color: #24243c !important;
    font-family: 'SF Pro Display', 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
}
.main-block {
    background: rgba(255,255,255,0.93);
    border-radius: 18px;
    box-shadow: 0 4px 36px 0 rgba(44,64,117,0.10), 0 1.5px 4px rgba(50,50,70,0.07);
    padding: 32px 32px 12px 32px;
    margin-bottom: 22px;
    border: 1px solid #f0f2fa;
}
.stButton>button {
    background: linear-gradient(90deg, #4066e0 0%, #7fbcfb 100%) !important;
    color: #fff !important;
    border-radius: 12px !important;
    border: none !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 12px rgba(64,130,255,0.13);
    transition: background 0.25s, box-shadow 0.2s;
    padding: 9px 28px;
    font-size: 18px;
    letter-spacing: 0.01em;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #2952b3 0%, #5eb3ee 100%) !important;
    box-shadow: 0 6px 24px rgba(56,108,244,0.13);
    color: #fff !important;
}
.stTextInput>div>div>input {
    background: #fafdff !important;
    border: 2px solid #dde4f4 !important;
    border-radius: 12px !important;
    padding: 11px 20px;
    font-size: 18px;
    color: #232445;
    font-weight: 500;
    box-shadow: none !important;
    transition: border 0.18s;
}
.stTextInput>div>div>input:focus {
    border: 2px solid #6c98fa !important;
    background: #fff !important;
}
h1, h2, h3, h4, h5, h6 {
    font-weight: 700 !important;
    color: #232445 !important;
    letter-spacing: 0.01em;
}
.track-list-row {
    padding: 8px 0 8px 0;
    border-bottom: 1px solid #f3f5fb;
    font-size: 17.2px;
}
.stCaption, .stMarkdown, .stSubheader {
    color: #395acf !important;
    font-weight:600;
}
.artist-img, .album-img {
    box-shadow: 0 4px 20px rgba(40,90,180,0.10);
    border-radius: 14px;
}
.desc-strong {
    color:#3147a1 !important;
    font-weight:700;
}
[data-testid="stHeader"] {
    background: transparent !important;
}
</style>
    """, unsafe_allow_html=True)

    # ========= 语言切换 ========= #
    if 'lang' not in st.session_state:
        st.session_state['lang'] = 'zh'
    lang = st.sidebar.selectbox("🌐 语言 / Language", ["中文", "English"], index=0 if st.session_state['lang']=='zh' else 1)
    lang_code = 'zh' if lang=="中文" else 'en'
    st.session_state['lang'] = lang_code
    T = TRANSLATIONS[lang_code]
    CONTINENT = CONTINENT_COUNTRIES if lang_code=='zh' else CONTINENT_COUNTRIES_EN

    # ========= 顶部标题与说明 ========= #
    st.title(f"🎵 {T['title']}")
    st.markdown(
        f"<div style='margin-bottom:12px;font-size:1.1em;color:#274bca;background:#f3f6ff;padding:9px 22px 9px 18px;border-radius:10px;display:inline-block;font-weight:700;'>{'📖 ' if lang_code=='zh' else '📖 '} {'一键查清专辑、艺人在全球的版权可用地区。' if lang_code=='zh' else 'Album/artist availability map at a glance.'}</div>",
        unsafe_allow_html=True,
    )

    # ========= 搜索主区块 ========= #
    tab = st.radio("", [T["search_tab"], T["album_link_tab"]], horizontal=True)

    # 搜索状态管理
    if 'artist_id' not in st.session_state: st.session_state['artist_id'] = None
    if 'album_id' not in st.session_state: st.session_state['album_id'] = None

    def clear_artist_album():
        st.session_state['artist_id'] = None
        st.session_state['album_id'] = None

    if tab == T["search_tab"]:
        search_val = st.text_input(f"{T['search_placeholder']}：", value="", key="search_input")
        col1, col2 = st.columns([1,3])
        with col1:
            if st.button(T["search_btn"]):
                st.session_state['artist_id'] = None
                st.session_state['album_id'] = None
                albums, artists = search_albums(search_val.strip(), limit=10)
                st.session_state['search_albums'] = albums
                st.session_state['search_artists'] = artists
                st.session_state['search_mode'] = "search"
        with col2:
            st.button("🔄 清空", on_click=clear_artist_album)
    else:
        album_url = st.text_input(T["album_link_tab"], placeholder=T["album_url_placeholder"], key="album_url")
        if st.button(T["query_btn"]):
            album_id = extract_album_id(album_url)
            if not album_id:
                st.error("请输入正确的Spotify专辑链接" if lang_code=='zh' else "Please enter a valid Spotify album link.")
            else:
                st.session_state['album_id'] = album_id
                st.session_state['artist_id'] = None
                st.session_state['search_mode'] = "album"
                st.session_state['search_albums'] = []
                st.session_state['search_artists'] = []

    # ========= 搜索结果展示 ========= #
    if st.session_state.get('search_mode') == "search" and (st.session_state.get('search_albums') or st.session_state.get('search_artists')):
        albums, artists = st.session_state['search_albums'], st.session_state['search_artists']
        # 艺人
        if artists:
            st.markdown(f"#### {T['artist_section']}")
            for artist in artists:
                with st.container():
                    c1, c2, c3 = st.columns([1,2,1])
                    with c1:
                        if artist.get("images"):
                            st.image(artist["images"][0]["url"], width=72, use_container_width=False, output_format='PNG', caption="")
                        else:
                            st.image("https://cdn-icons-png.flaticon.com/512/727/727245.png", width=64)
                    with c2:
                        st.markdown(f"<span class='desc-strong'>{artist['name']}</span>", unsafe_allow_html=True)
                        genres = ", ".join(artist['genres']) if artist.get('genres') else ""
                        st.caption((f"{T['genres']}: {genres}  ") if genres else "")
                        st.caption((f"{T['followers']}: {artist.get('followers',{}).get('total',0):,}"))
                    with c3:
                        if st.button(T["view_albums"], key=f"artist_{artist['id']}"):
                            st.session_state['artist_id'] = artist['id']
                            st.session_state['album_id'] = None
                            st.session_state['search_mode'] = "artist"
                            st.rerun()
        # 专辑
        if albums:
            st.markdown(f"#### {T['album_section']}")
            for album in albums:
                with st.container():
                    c1, c2, c3 = st.columns([1,2,1])
                    with c1:
                        if album.get("images"):
                            st.image(album["images"][0]["url"], width=72, use_container_width=False, output_format='PNG')
                        else:
                            st.image("https://cdn-icons-png.flaticon.com/512/727/727245.png", width=64)
                    with c2:
                        alb_name = album['name']
                        artists_line = ", ".join(a['name'] for a in album['artists'])
                        alb_year = album.get('release_date', '')[:4]
                        st.markdown(f"<span class='desc-strong'>{alb_name}</span>", unsafe_allow_html=True)
                        st.caption(f"{T['artist']}: {artists_line}  {T['release_date']}: {alb_year}")
                    with c3:
                        if st.button(T["view_region"], key=f"alb_{album['id']}"):
                            st.session_state['album_id'] = album['id']
                            st.session_state['artist_id'] = album['artists'][0]['id'] if album['artists'] else None
                            st.session_state['search_mode'] = "album"
                            st.rerun()

    # ========= 艺人专辑列表 ========= #
    if st.session_state.get('search_mode') == "artist" and st.session_state.get('artist_id') and not st.session_state.get('album_id'):
        st.markdown('<div class="main-block">', unsafe_allow_html=True)
        albums = get_artist_albums(st.session_state['artist_id'])
        st.subheader(T["artist_albums_title"])
        if not albums:
            st.info(T["no_artist_album"])
        else:
            for album in albums[:12]:
                c1, c2 = st.columns([1,5])
                with c1:
                    if album.get('images'):
                        st.image(album['images'][0]['url'], width=54, use_container_width=False, output_format='PNG')
                    else:
                        st.image("https://cdn-icons-png.flaticon.com/512/727/727245.png", width=48)
                with c2:
                    btn = st.button(f"{album['name']} ({album['release_date'][:4]})", key=f"artist_album_{album['id']}")
                    if btn:
                        st.session_state['album_id'] = album['id']
                        st.session_state['search_mode'] = "album"
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ========= 专辑详情/地区分布 ========= #
    if st.session_state.get('search_mode') == "album" and st.session_state.get('album_id'):
        album_id = st.session_state.get('album_id')
        st.markdown('<div class="main-block">', unsafe_allow_html=True)
        progress = st.progress(0)
        placeholder = st.empty()
        placeholder.text(T["loading_album"])
        try:
            start_time = time.time()
            progress.progress(25)
            album = get_album_data(album_id)
            st.session_state['artist_id'] = album['artists'][0]['id'] if album.get('artists') else None
            placeholder.text(T["loading_track"])
            progress.progress(65)
            load_time = time.time() - start_time
            placeholder.empty()
            progress.progress(100)
            st.caption(T["loading_time"].format(time=load_time))

            col1, col2 = st.columns([1, 3])
            with col1:
                if album.get('images'):
                    st.image(album['images'][0]['url'], width=180, use_container_width=True, output_format='PNG')
                if album.get('external_urls', {}).get('spotify'):
                    st.markdown(f"[Open in Spotify]({album['external_urls']['spotify']})")
            with col2:
                st.markdown(
                    f"<h2 style='color:#232445;font-size:2.3rem;font-weight:700;margin-bottom:8px'>{album.get('name', '未知专辑')}</h2>",
                    unsafe_allow_html=True
                )
                st.markdown(f"👤 <b>{T['artist']}</b>：" + ", ".join(artist['name'] for artist in album.get('artists', [])), unsafe_allow_html=True)
                st.write(f"📅 **{T['release_date']}**：{album.get('release_date', 'N/A')}")
                st.write(f"💽 **{T['album_type']}**：{album.get('album_type', 'N/A').capitalize()}")
                st.write(f"⭐ **{T['popularity']}**：{album.get('popularity', 0)}/100")
                if album.get('genres'):
                    st.write(f"🎼 **{T['genres']}**：{', '.join(album['genres'])}")
                st.write(f"👥 **{T['followers']}**：{album.get('artist_followers', 0):,}")
                if album.get('artist_url'):
                    st.write(f"🔗 **{T['artist_link']}**：[Spotify]({album['artist_url']})")
            st.markdown("---")
            st.subheader(T["track_list_title"])
            sort_option = st.selectbox(
                T["sort_track"],
                [T["sort_order"], T["sort_popularity"]],
                key="sort_tracks"
            )
            sorted_tracks = album.get('tracks', [])
            if sort_option == T["sort_popularity"]:
                sorted_tracks = sorted(
                    sorted_tracks,
                    key=lambda x: x.get('popularity', 0),
                    reverse=True
                )

            main_artist_names = [artist['name'] for artist in album.get('artists', [])]

            for idx, track in enumerate(sorted_tracks, 1):
                duration_ms = track.get('duration_ms', 0)
                minutes = duration_ms // 60000
                seconds = (duration_ms % 60000) // 1000
                duration = f"{minutes}:{seconds:02d}"
                track_artist_names = [a['name'] for a in track.get('artists', [])]

                # 只有当track的艺人和专辑主艺人完全一致时不显示
                if track_artist_names == main_artist_names:
                    artist_part = ""
                else:
                    artist_part = f"<br>{T['artist']}: {', '.join(track_artist_names)}"
                
                st.markdown(
                    f"<div class='track-list-row'>{idx}. <b>{track.get('name', 'Unknown Track')}</b> "
                    f"<span style='color:#889;'>({duration})</span> - {T['popularity']}: {track.get('popularity', 0)}/100{artist_part}</div>",
                    unsafe_allow_html=True
                )
            st.markdown("---")
            markets = album.get('available_markets', [])
            if markets:
                total_markets = len(markets)
                st.subheader(T["region_dist_title"].format(total=total_markets))
                st.caption(T["region_dist_caption"])
                continent_data = defaultdict(list)
                for continent, countries in CONTINENT.items():
                    for code, name in countries:
                        if code in markets:
                            continent_data[continent].append((name, code))
                stats = {continent: len(countries) for continent, countries in continent_data.items()}
                import plotly.express as px
                fig = px.bar(
                    x=list(stats.keys()),
                    y=list(stats.values()),
                    labels={'x': 'Continent', 'y': 'Country/Region Count'} if lang_code=='en' else {'x': '大洲', 'y': '国家/地区数量'},
                    color=list(stats.keys()),
                    color_discrete_sequence=px.colors.sequential.Blues
                )
                fig.update_layout(
                    xaxis_title="Continent" if lang_code=='en' else "大洲",
                    yaxis_title="Country/Region Count" if lang_code=='en' else "国家/地区数量",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                num_cols = 3
                for continent, countries in continent_data.items():
                    countries.sort(key=lambda x: x[0])
                    st.markdown(f"#### {continent}")
                    cols = st.columns(num_cols)
                    for i, (name, code) in enumerate(countries):
                        cols[i % num_cols].write(f"✅ {name} ({code})")
            else:
                st.warning(T["no_markets"])
        except Exception as e:
            placeholder.empty()
            progress.progress(100)
            st.error(T["error_fetch"])
            logger.error(f"Fetch failed: {str(e)} [Type: General]", exc_info=True)
            if "429" in str(e):
                st.warning("API请求超限，需等待 3 秒，建议稍后重试。")
        st.markdown('</div>', unsafe_allow_html=True)

    # 使用说明（始终底部浮动）
    with st.expander(T["usage_title"]):
        st.markdown(T["usage_content"])

    st.caption(T["powered"])

if __name__ == "__main__":
    main()
