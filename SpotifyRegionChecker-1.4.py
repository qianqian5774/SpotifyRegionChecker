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
import plotly.express as px

# ==== 日志系统设置（仅限管理员） ==== #
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 文件处理器：带轮换的日志文件
file_handler = RotatingFileHandler('spotify_app.log', maxBytes=5*1024*1024, backupCount=3)  # 5MB, 3 backups
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 控制台处理器：输出到Streamlit控制台
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("✅ 程序已启动，日志系统初始化成功")

# ==== Spotify API 授权 ==== #
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    st.error("错误：缺少Spotify API凭证。请检查环境变量配置。")
    logger.error("Missing Spotify API credentials [Type: Config]")
    st.stop()

# 创建Spotify API连接
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# 定义各大洲的主要国家
CONTINENT_COUNTRIES = {
    "亚洲": [
        ("CN", "中国"), ("TW", "台湾"), ("HK", "香港"),
        ("JP", "日本"), ("SG", "新加坡"), 
        ("TH", "泰国"), ("VN", "越南"), ("ID", "印尼")
    ],
    "欧洲": [
        ("GB", "英国"), ("FR", "法国"), ("DE", "德国"), 
        ("ES", "西班牙"), ("NL", "荷兰"), ("SE", "瑞典"), 
        ("BE", "比利时")
    ],
    "北美洲": [
        ("US", "美国"), ("CA", "加拿大"), ("MX", "墨西哥")
    ],
    "南美洲": [
        ("BR", "巴西"), ("AR", "阿根廷"), ("CL", "智利"),
        ("CO", "哥伦比亚"), ("PE", "秘鲁")
    ],
    "大洋洲": [
        ("AU", "澳大利亚"), ("NZ", "新西兰")
    ],
    "非洲": [
        ("ZA", "南非"), ("EG", "埃及"), ("NG", "尼日利亚")
    ]
}

# 多语言翻译字典
TRANSLATIONS = {
    "zh": {
        "title": "Spotify 专辑地区查询",
        "input_url": "请输入 Spotify 专辑链接",
        "url_placeholder": "例如：https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "example": "示例链接: https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "search_btn": "查询专辑信息",
        "refresh_btn": "刷新数据",
        "try_example": "试用示例",
        "search_input": "搜索专辑或艺术家",
        "search_placeholder": "例如：Taylor Swift",
        "loading_album": "正在加载专辑信息...",
        "loading_time": "查询耗时: {time:.2f}秒",
        "artist": "艺术家",
        "release_date": "发行日期",
        "album_type": "专辑类型",
        "genres": "流派",
        "tracks": "曲目列表",
        "availability": "🌍 专辑在 {total} 个地区可用",
        "availability_note": "以下仅显示各大洲代表性国家",
        "region_dist": "可用地区分布",
        "no_markets": "⚠️ 此专辑的地区信息不可用",
        "no_markets_info": "可能原因：专辑刚发布信息未同步、特殊版权限制或API暂时不可用",
        "invalid_url": "请输入有效的Spotify专辑链接！",
        "invalid_format": "无效的Spotify专辑链接！请使用正确的格式。",
        "error_fetch": "获取专辑信息失败，请稍后重试或检查链接",
        "no_results": "未找到匹配的专辑或艺术家，请检查输入！",
        "popularity": "流行度",
        "followers": "关注者",
        "artist_link": "艺术家链接",
        "rate_limit": "API请求超限，需等待 {delay} 秒，建议稍后重试。",
        "loading_step_album": "正在获取专辑信息...",
        "loading_step_tracks": "正在加载曲目和地区数据...",
        "sort_error": "排序失败，无法加载曲目流行度，请刷新重试。",
        "powered_by": "由 Spotify 提供支持",
        "usage_guide": "使用说明",
        "guide_content": "1. 输入Spotify专辑URL或搜索艺术家/专辑\n2. 点击‘查询专辑信息’查看详情\n3. 使用‘排序’选项按流行度查看曲目\n4. 点击‘刷新数据’更新结果\n5. 数据来自Spotify Web API，仅用于显示，不会存储或用于其他目的",
        "cache_cleared": "数据已刷新，请重新查询"
    },
    "en": {
        "title": "Spotify Album Region Checker",
        "input_url": "Enter Spotify album URL",
        "url_placeholder": "e.g., https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "example": "Example: https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        "search_btn": "Search Album Info",
        "refresh_btn": "Refresh Data",
        "try_example": "Try Example",
        "search_input": "Search album or artist",
        "search_placeholder": "e.g., Taylor Swift",
        "loading_album": "Loading album information...",
        "loading_time": "Query time: {time:.2f} seconds",
        "artist": "Artist",
        "release_date": "Release Date",
        "album_type": "Album Type",
        "genres": "Genres",
        "tracks": "Track List",
        "availability": "🌍 Album available in {total} regions",
        "availability_note": "Only representative countries per continent are shown below",
        "region_dist": "Region Availability Distribution",
        "no_markets": "⚠️ Region info for this album is unavailable",
        "no_markets_info": "Possible reasons: newly released album, special copyright restrictions, or API temporarily unavailable",
        "invalid_url": "Please enter a valid Spotify album URL!",
        "invalid_format": "Invalid Spotify album URL! Please use the correct format.",
        "error_fetch": "Failed to fetch album info, please try again later or check the URL",
        "no_results": "No matching albums or artists found, please check your input!",
        "popularity": "Popularity",
        "followers": "Followers",
        "artist_link": "Artist Link",
        "rate_limit": "API rate limit exceeded, wait {delay} seconds, please try again later.",
        "loading_step_album": "Fetching album details...",
        "loading_step_tracks": "Loading tracks and region data...",
        "sort_error": "Sorting failed, unable to load track popularity, please refresh and try again.",
        "powered_by": "Powered by Spotify",
        "usage_guide": "Usage Guide",
        "guide_content": "1. Enter a Spotify album URL or search for an album/artist\n2. Click 'Search Album Info' to view details\n3. Use 'Sort' to view tracks by popularity\n4. Click 'Refresh Data' to update results\n5. Data is sourced from the Spotify Web API, used only for display, and not stored or used for other purposes",
        "cache_cleared": "Data refreshed, please query again"
    }
}

def extract_album_id(url):
    """从Spotify专辑链接提取专辑ID。"""
    if not url or not isinstance(url, str):
        return None
    pattern = r"(?:spotify\.com/album/|:album:)([\w\d]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@st.cache_data(ttl=3600, show_spinner=False)  # 1小时缓存
def get_album_data(album_id):
    """获取并缓存Spotify专辑数据。"""
    if not album_id or not isinstance(album_id, str):
        logger.error("Invalid album ID provided [Type: Input]")
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
            if e.http_status == 429 and attempt < retries:
                retry_after = int(e.headers.get('Retry-After', 2))
                logger.warning(f"Rate limit hit for album {album_id}, retry after {retry_after}s [Type: API]")
                time.sleep(retry_after)
                continue
            logger.error(f"Spotify API error for album {album_id}: {str(e)} [Type: API]")
            raise Exception("Spotify API错误")
        except Exception as e:
            logger.error(f"Failed to fetch album data for {album_id}: {str(e)} [Type: General]")
            raise Exception("获取专辑数据失败")

@st.cache_data(ttl=3600, show_spinner=False)  # 1小时缓存
def search_albums(query, limit=10):
    """搜索专辑或艺术家。"""
    if not query or not isinstance(query, str):
        logger.error("Invalid search query provided [Type: Input]")
        return []
    retries = 2
    for attempt in range(retries + 1):
        try:
            results = sp.search(q=query, type='album', limit=limit)
            logger.info(f"Search successful for query: {query} [Type: API]")
            return results['albums']['items']
        except spotipy.SpotifyException as e:
            if e.http_status == 429 and attempt < retries:
                retry_after = int(e.headers.get('Retry-After', 2))
                logger.warning(f"Rate limit hit for search {query}, retry after {retry_after}s [Type: API]")
                time.sleep(retry_after)
                continue
            logger.error(f"Spotify API error for search {query}: {str(e)} [Type: API]")
            raise Exception("Spotify API错误")
        except Exception:
            logger.error(f"Search failed for {query} [Type: General]")
            return []

def main():
    """主函数：运行优化版Spotify专辑地区查询应用。"""
    st.set_page_config(
        page_title="Spotify 专辑地区查询", 
        page_icon="🎵", 
        layout="wide"
    )
    
    # 注入自定义 CSS
    st.markdown("""
        <style>
        .stButton>button {
            background-color: #1DB954;
            color: white;
            border-radius: 8px;
        }
        .stTextInput>div>div>input {
            border: 2px solid #1DB954;
            border-radius: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 初始化会话状态
    if 'lang' not in st.session_state:
        st.session_state['lang'] = "中文"
    if 'album_id' not in st.session_state:
        st.session_state['album_id'] = None
    
    # 语言选择
    lang = st.selectbox("语言 / Language", ["中文", "English"], key="lang")
    lang_code = "zh" if lang == "中文" else "en"
    t = TRANSLATIONS[lang_code]
    
    # 显示标题
    st.title(f"🎵 {t['title']}")
    
    # 使用说明
    with st.expander(t["usage_guide"]):
        st.markdown(t["guide_content"])
    
    # 搜索专辑或艺术家
    search_query = st.text_input(
        t["search_input"], 
        placeholder=t["search_placeholder"],
        key="search_query"
    )
    
    if search_query:
        progress = st.progress(0)
        placeholder = st.empty()
        placeholder.text(t["loading_album"])
        try:
            progress.progress(33)
            results = search_albums(search_query)
            placeholder.empty()
            progress.progress(100)
            if not results:
                st.warning(t["no_results"])
            else:
                for item in results:
                    if st.button(
                        f"{item['name']} - {', '.join(a['name'] for a in item['artists'])}", 
                        key=item['id']
                    ):
                        st.session_state['album_id'] = item['id']
                        logger.info(f"User selected album: {item['id']} [Type: User]")
        except Exception as e:
            placeholder.empty()
            progress.progress(100)
            st.error(t["error_fetch"])
            logger.error(f"Search failed: {str(e)} [Type: General]")
            if "429" in str(e):
                retry_after = e.headers.get('Retry-After', 'a few')
                st.warning(t["rate_limit"].format(delay=retry_after))
    
    # 输入框和查询按钮
    album_url = st.text_input(
        t["input_url"], 
        placeholder=t["url_placeholder"],
        key="album_url"
    )
    st.caption(t["example"])
    if st.button(t["try_example"]):
        st.session_state['album_id'] = "4aawyAB9vmqN3uQ7FjRGTy"
        logger.info("User triggered example album: 4aawyAB9vmqN3uQ7FjRGTy [Type: User]")
    
    col1, col2 = st.columns(2)
    with col1:
        search_btn = st.button(t["search_btn"])
    with col2:
        refresh_btn = st.button(t["refresh_btn"])
    
    # 刷新缓存
    if refresh_btn:
        st.cache_data.clear()
        st.session_state['album_id'] = None
        logger.info("Cache cleared and session reset by user [Type: User]")
        st.success(t["cache_cleared"])
        st.rerun()
    
    # 处理专辑ID
    if search_btn and album_url:
        album_url = album_url.strip()
        if not album_url:
            st.error(t["invalid_url"])
        else:
            album_id = extract_album_id(album_url)
            if not album_id:
                st.error(f"{t['invalid_format']} 请确保链接包含'album'，如：{t['url_placeholder']}")
            else:
                st.session_state['album_id'] = album_id
                logger.info(f"User submitted album ID: {album_id} [Type: User]")
    
    # 显示专辑信息
    if st.session_state['album_id']:
        progress = st.progress(0)
        placeholder = st.empty()
        placeholder.text(t["loading_step_album"])
        try:
            start_time = time.time()
            progress.progress(33)
            album = get_album_data(st.session_state['album_id'])
            placeholder.text(t["loading_step_tracks"])
            progress.progress(66)
            load_time = time.time() - start_time
            placeholder.empty()
            progress.progress(100)
            st.caption(t["loading_time"].format(time=load_time))
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if album.get('images'):
                    st.image(album['images'][0]['url'], width=200, use_container_width=True)
            with col2:
                st.markdown(f"<h2 style='color: #1DB954;'>{album.get('name', 'Unknown Album')}</h2>", unsafe_allow_html=True)
                st.write(f"**{t['artist']}:** {', '.join(artist['name'] for artist in album.get('artists', []))}")
                st.write(f"**{t['release_date']}:** {album.get('release_date', 'N/A')}")
                st.write(f"**{t['album_type']}:** {album.get('album_type', 'N/A').capitalize()}")
                st.write(f"**{t['popularity']}:** <span style='color: #1DB954;'>{album.get('popularity', 0)}/100</span>", unsafe_allow_html=True)
                if album.get('genres'):
                    st.write(f"**{t['genres']}:** {', '.join(album['genres'])}")
                st.write(f"**{t['followers']}:** {album.get('artist_followers', 0):,}")
                st.write(f"**{t['artist_link']}:** [Spotify]({album.get('artist_url', '')})")
            
            st.markdown("---")
            st.subheader(f"🎸 {t['tracks']}")
            sort_option = st.selectbox(
                "Sort Tracks By", 
                ["Track Order", "Popularity"], 
                key="sort_tracks"
            )
            try:
                sorted_tracks = album.get('tracks', [])
                if not sorted_tracks:
                    st.warning("无曲目数据可用")
                elif sort_option == "Popularity":
                    sorted_tracks = sorted(
                        sorted_tracks, 
                        key=lambda x: x.get('popularity', 0), 
                        reverse=True
                    )
                for track in sorted_tracks:
                    duration_ms = track.get('duration_ms', 0)
                    minutes = duration_ms // 60000
                    seconds = (duration_ms % 60000) // 1000
                    duration = f"{minutes}:{seconds:02d}"
                    st.write(f"- {track.get('name', 'Unknown Track')} ({duration}) - {t['popularity']}: {track.get('popularity', 0)}/100")
            except Exception as e:
                st.error(t["sort_error"])
                logger.error(f"Track sorting failed: {str(e)} [Type: General]")
            
            st.markdown("---")
            markets = album.get('available_markets', [])
            
            if markets:
                total_markets = len(markets)
                st.subheader(t["availability"].format(total=total_markets))
                st.caption(t["availability_note"])
                
                continent_data = defaultdict(list)
                for continent, countries in CONTINENT_COUNTRIES.items():
                    for code, name in countries:
                        if code in markets:
                            continent_data[continent].append((name, code))
                
                st.subheader(t["region_dist"])
                stats = {continent: len(countries) for continent, countries in continent_data.items()}
                fig = px.bar(
                    x=list(stats.keys()),
                    y=list(stats.values()),
                    labels={'x': 'Continent', 'y': 'Number of Countries'},
                    color=list(stats.keys()),
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                fig.update_layout(
                    xaxis_title="Continent",
                    yaxis_title="Number of Countries",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                
                num_cols = 3
                for continent, countries in continent_data.items():
                    countries.sort(key=lambda x: x[0])  # 按名称排序
                    st.markdown(f"#### {continent}")
                    cols = st.columns(num_cols)
                    for i, (name, code) in enumerate(countries):
                        cols[i % num_cols].write(f"✓ {name} ({code})")
                    st.markdown("---")
            else:
                st.warning(t["no_markets"])
                st.info(t["no_markets_info"])
        except Exception as e:
            placeholder.empty()
            progress.progress(100)
            st.error(t["error_fetch"])
            logger.error(f"Fetch failed: {str(e)} [Type: General]")
            if "429" in str(e):
                retry_after = e.headers.get('Retry-After', 'a few')
                st.warning(t["rate_limit"].format(delay=retry_after))
    
    # Spotify 归因
    st.markdown("---")
    st.caption(f"{t['powered_by']} | <a href='https://www.spotify.com' target='_blank'>Spotify</a>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()