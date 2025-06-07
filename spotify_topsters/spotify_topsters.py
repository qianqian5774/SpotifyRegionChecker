import os
import time
import logging
from logging.handlers import RotatingFileHandler
from io import BytesIO
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==== 语言与主题 ====
LANGS = {
    "zh": {
        "flag": "🇨🇳", "bg_desc": "背景色", "tile_desc": "拼图边框色", "spacing": "专辑图片间距(px)",
        "time_range": "时间范围", "collage_type": "拼图类型", "grid_size": "拼图格数(2-15)",
        "fold_params": "🎛️ 拼图参数",
        "export_type": "导出格式", "png": "PNG", "jpg": "JPG",
        "export_btn": "⬇️ 下载拼图", "download_list": "🗒️ 导出列表图片",
        "fetching": "正在获取你的 Spotify 数据…", "error_data": "没有获取到足够数据，请确保最近有听歌记录。",
        "list_title_album": "🎵 专辑列表", "list_title_track": "🎶 歌曲列表", "list_title_artist": "👤 艺术家列表",
        "powered": "©️ Powered by Spotipy & Streamlit · 设计灵感：二千"
    },
    "en": {
        "flag": "🇬🇧", "bg_desc": "Background Color", "tile_desc": "Tile Border Color", "spacing": "Tile Spacing (px)",
        "time_range": "Time Range", "collage_type": "Collage Type", "grid_size": "Grid Size (2-15)",
        "fold_params": "🎛️ Collage Params",
        "export_type": "Export Format", "png": "PNG", "jpg": "JPG",
        "export_btn": "⬇️ Download Collage", "download_list": "🗒️ Export List Image",
        "fetching": "Fetching your Spotify data...", "error_data": "No enough data, please ensure recent listening history.",
        "list_title_album": "🎵 Album List", "list_title_track": "🎶 Track List", "list_title_artist": "👤 Artist List",
        "powered": "©️ Powered by Spotipy & Streamlit · Inspired by topsters.org"
    }
}
THEMES = {
    "light": {
        "bg": "#fafcff",
        "text": "#111111",
        "border": "#e0e0e0",
        "list_bg": "#f6f8fb",
        "preset": {
            "经典白": "#ffffff",
            "暖灰": "#f5f5f5",
            "淡蓝": "#f0f8ff"
        }
    },
    "dark": {
        "bg": "#232529",
        "text": "#eeeeee",
        "border": "#333333",
        "list_bg": "#232529",
        "preset": {
            "经典黑": "#000000",
            "深灰": "#1a1a1a",
            "深蓝": "#1a1f3a"
        }
    }
}

if "lang" not in st.session_state: st.session_state["lang"] = "zh"
if "theme" not in st.session_state: st.session_state["theme"] = "light"
lang = st.session_state["lang"]
theme = st.session_state["theme"]
TR = LANGS[lang]
current_theme = THEMES[theme]
def tr(key): return TR.get(key, key)

# ==== 顶部LOGO及切换 ====
col_left, _, col_right = st.columns([1,8,1])
with col_left:
    if st.button(TR["flag"], key="lang_btn"):
        st.session_state["lang"] = "en" if lang == "zh" else "zh"
        st.rerun()
with col_right:
    if st.button("🌞" if theme == "light" else "🌙", key="theme_btn"):
        st.session_state["theme"] = "dark" if theme == "light" else "light"
        st.rerun()
# 主题和语言刷新
lang = st.session_state["lang"]
theme = st.session_state["theme"]
TR = LANGS[lang]
current_theme = THEMES[theme]

st.markdown(f"""
    <div style='text-align:center;margin-top:2px;margin-bottom:24px;font-size:1.14em;color:{current_theme["text"]};opacity:0.89;'>
        一键生成你的专属拼图 · 支持专辑、歌曲、艺人
    </div>
""" if lang=="zh" else """
    <div style='text-align:center;margin-top:2px;margin-bottom:24px;font-size:1.14em;color:#222;opacity:0.89;'>
        One-click collage for your Spotify favorites · Albums / Tracks / Artists
    </div>
""", unsafe_allow_html=True)

# ==== 日志与环境变量 ====
log_path = "spotify_topsters.log"
handler = RotatingFileHandler(log_path, maxBytes=1024*1024, backupCount=3, encoding="utf-8")
logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
def clean_cache_folder(folder="./.cache", interval_sec=12*3600):
    now = time.time()
    for root, dirs, files in os.walk(folder):
        for f in files:
            path = os.path.join(root, f)
            if now - os.path.getmtime(path) > interval_sec:
                try:
                    os.remove(path)
                    logging.info(f"Cache cleaned: {path}")
                except Exception as e:
                    logging.warning(f"Cache clean failed: {e}")
clean_cache_folder(".cache", interval_sec=12*3600)

load_dotenv()
SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI  = os.getenv("SPOTIPY_REDIRECT_URI")
if not (SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI):
    st.error("请检查 .env 是否配置了 SPOTIPY_CLIENT_ID、SPOTIPY_CLIENT_SECRET、SPOTIPY_REDIRECT_URI" if lang=="zh" else "Please check .env for SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI")
    st.stop()

# ==== 拼图参数 ====
with st.expander(tr("fold_params"), expanded=True):
    param_cols = st.columns([2,2,2])
    with param_cols[0]:
        bg_color = st.color_picker(tr("bg_desc"), value=current_theme["bg"], key="bg_color")
        preset_theme = st.selectbox(
            "🎨 " + (tr("bg_desc") + "预设" if lang=="zh" else "Preset Themes"),
            ["自定义"] + list(current_theme["preset"].keys()), index=0)
        if preset_theme != "自定义":
            bg_color = current_theme["preset"][preset_theme]
    with param_cols[1]:
        border_color = st.color_picker(tr("tile_desc"), value=current_theme["border"], key="border_color")
        tile_gap = st.slider(tr("spacing"), 0, 32, 4, label_visibility="visible")
    with param_cols[2]:
        grid = st.number_input(tr("grid_size"), min_value=2, max_value=15, value=5, step=1)
        num = int(grid) * int(grid)

time_opts = [("近一个月", "short_term"), ("近三个月", "medium_term"), ("全部时间", "long_term")] if lang=="zh" else [("Last month", "short_term"), ("Last 3 months", "medium_term"), ("All time", "long_term")]
time_labels = [x[0] for x in time_opts]
label_to_value = dict(time_opts)
selected_time_label = st.selectbox(tr("time_range"), options=time_labels)
use_time = label_to_value[selected_time_label]

top_types = [("Top 专辑", "album"), ("Top 歌曲", "track"), ("Top 艺术家", "artist")] if lang=="zh" else [("Top Albums", "album"), ("Top Tracks", "track"), ("Top Artists", "artist")]
top_labels = [x[0] for x in top_types]
top_label_to_value = dict(top_types)
selected_top_label = st.radio(tr("collage_type"), options=top_labels, horizontal=True)
type_key = top_label_to_value[selected_top_label]

# ==== 授权逻辑 ====
scope = "user-top-read user-read-recently-played"
oauth_manager = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=scope,
    show_dialog=True,
    cache_path=".spotify_token_cache"
)
try:
    query_params = st.query_params
except AttributeError:
    query_params = st.experimental_get_query_params()
code = query_params.get("code", None)
if isinstance(code, list): code = code[0]
if "token_info" not in st.session_state:
    if not code:
        auth_url = oauth_manager.get_authorize_url()
        st.markdown(
            f"<div style='text-align:center;margin-top:18px;'><a href='{auth_url}' target='_self'><button style='background:#1db954;color:#fff;border:0;font-size:1.18em;padding:0.8em 2.8em;border-radius:12px;box-shadow:0 4px 18px #2223;'>{'🎧 登录 Spotify 授权' if lang=='zh' else '🎧 Login Spotify'}</button></a></div>",
            unsafe_allow_html=True)
        st.stop()
    else:
        try:
            token_info = oauth_manager.get_access_token(code, as_dict=True)
            st.session_state["token_info"] = token_info
            st.success("✅ 授权成功！正在生成拼图..." if lang=="zh" else "✅ Authorized! Generating...")
            st.rerun()
        except Exception as e:
            st.error("❌ 获取Token失败，请检查Redirect URI设置" if lang=="zh" else "❌ Token failed, check Redirect URI")
            st.write("错误详情：" if lang=="zh" else "Error: ", e)
            st.stop()
token_info = st.session_state["token_info"]
sp = Spotify(auth=token_info["access_token"])

# ==== 数据获取 ====
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_top_items_unique_cover(type="album", limit=9, time_range="short_term"):
    try:
        items, cover_urls = [], set()
        if type == "album":
            top_tracks = sp.current_user_top_tracks(limit=50, time_range=time_range)
            for item in top_tracks["items"]:
                album = item["album"]
                img_list = album.get("images", [])
                img_url = max(img_list, key=lambda x: x.get('width',0)*x.get('height',0))["url"] if img_list else None
                if img_url and img_url not in cover_urls:
                    items.append(album)
                    cover_urls.add(img_url)
                if len(items) >= limit:
                    break
            return items
        elif type == "track":
            for item in sp.current_user_top_tracks(limit=50, time_range=time_range)["items"]:
                img_list = item["album"].get("images", [])
                img_url = max(img_list, key=lambda x: x.get('width',0)*x.get('height',0))["url"] if img_list else None
                if img_url and img_url not in cover_urls:
                    items.append(item)
                    cover_urls.add(img_url)
                if len(items) >= limit:
                    break
            return items
        elif type == "artist":
            result = sp.current_user_top_artists(limit=limit, time_range=time_range)
            for item in result["items"]:
                img_list = item.get("images", [])
                img_url = max(img_list, key=lambda x: x.get('width',0)*x.get('height',0))["url"] if img_list else None
                if img_url and img_url not in cover_urls:
                    items.append(item)
                    cover_urls.add(img_url)
                if len(items) >= limit:
                    break
            return items
        else:
            return []
    except Exception as e:
        logging.error(f"Spotify API error: {e}")
        return []

with st.spinner(tr("fetching")):
    top_items = fetch_top_items_unique_cover(type=type_key, limit=num, time_range=use_time)
if not top_items:
    st.error(tr("error_data"))
    st.stop()

# ==== 封面缓存 + 进度条 ====
def get_best_img_url(img_list):
    if not img_list: return None
    best = max(img_list, key=lambda x: x.get('width', 0)*x.get('height', 0))
    return best["url"]

def get_square_img(img_url):
    try:
        resp = requests.get(img_url, timeout=10)
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        w, h = img.size
        if w != h:
            edge = min(w, h)
            left = (w - edge)//2
            top = (h - edge)//2
            img = img.crop((left, top, left + edge, top + edge))
        return img
    except Exception:
        return Image.new("RGB", (320,320),(230,233,235))

img_urls = []
if type_key == "album":
    img_urls = [get_best_img_url(x["images"]) for x in top_items]
elif type_key == "track":
    img_urls = [get_best_img_url(x["album"]["images"]) for x in top_items]
elif type_key == "artist":
    img_urls = [get_best_img_url(x["images"]) if x.get("images") else None for x in top_items]

covers = []
with st.spinner(tr("fetching")):
    progress = st.progress(0)
    with ThreadPoolExecutor(max_workers=min(16, max(4, num))) as executor:
        future_to_idx = {executor.submit(get_square_img, url): idx for idx, url in enumerate(img_urls)}
        for count, future in enumerate(as_completed(future_to_idx)):
            idx = future_to_idx[future]
            img = future.result()
            covers.append((idx, img))
            progress.progress((count+1)/num)
covers = [img for idx, img in sorted(covers)]

# ==== 拼图生成 ====
def make_collage(covers, grid, gap, bg, border, font_size=36, export_size=1000):
    cell_size = max(80, int(export_size//int(grid) - gap))
    canvas_size = cell_size * int(grid) + gap * (int(grid)+1)
    canvas = Image.new("RGB", (canvas_size, canvas_size), color=bg)
    draw = ImageDraw.Draw(canvas)
    border_w = 2 if border.lower()!=bg.lower() else 0
    for idx, img in enumerate(covers):
        row, col = divmod(idx, int(grid))
        x = gap + col * (cell_size + gap)
        y = gap + row * (cell_size + gap)
        img = img.resize((cell_size, cell_size))
        canvas.paste(img, (x, y))
        if border_w > 0:
            draw.rectangle([x, y, x+cell_size, y+cell_size], outline=border, width=border_w)
    return canvas

def get_item_text(idx, item, type_key):
    if type_key == "artist":
        return f"{idx+1}. {item.get('name','N/A')}"
    else:
        artist = item.get('artists',[{'name':'N/A'}])[0].get('name','N/A')
        return f"{idx+1}. {item.get('name','N/A')} — {artist}"

def make_list_image(top_items, covers, type_key, theme):
    font_options = [
        "arial.ttf",
        "msyh.ttc",
        "simhei.ttf",
        "simsun.ttc",
        "微软雅黑.ttf",
        "arial unicode.ttf"
    ]
    font = None
    for font_name in font_options:
        try:
            font = ImageFont.truetype(font_name, 27)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
        logging.warning("Failed to load custom font, using default")
    h, w, y = 74 * len(top_items) + 48, 720, 32
    out = Image.new("RGB", (w, h), color="#fafcff" if theme == "light" else "#232529")
    draw = ImageDraw.Draw(out)
    for idx, (item, img) in enumerate(zip(top_items, covers)):
        try: out.paste(img.resize((56,56)), (22, y))
        except: pass
        try: draw.text((92, y+12), get_item_text(idx, item, type_key), fill="#111" if theme == "light" else "#eee", font=font)
        except: pass
        y += 74
    buf2 = BytesIO(); out.save(buf2, format="PNG"); return buf2.getvalue()

def render_list_item(idx, item, type_key, theme):
    url = item.get("external_urls", {}).get("spotify", "#")
    name = item.get("name", "N/A")
    artist = "" if type_key == "artist" else item.get("artists",[{'name':''}])[0].get("name","")
    bg = "#f6f8fb" if theme == "light" else "#232529"
    border = "#e0e0e0" if theme == "light" else "#333"
    txt_color = current_theme['text']
    st.markdown(
        f"""<div class='list-item' style='display:flex;align-items:center;gap:16px;
        padding:12px 18px;border-bottom:1px solid {border};background:{bg};
        border-radius:10px;margin-bottom:6px;transition:background 0.2s, box-shadow 0.2s;font-size:1.08em;'>
        <span style='font-size:1.1em;font-weight:700;width:32px;color:#1db954;'>{idx}.</span>
        <a href='{url}' target='_blank' style='color:#1db954;text-decoration:none;font-weight:bold;flex:1;'>{name}</a>
        {f"<span style='color:{txt_color};opacity:0.85;font-size:1em;margin-left:8px;'>{artist}</span>" if artist else ""}
        </div>""", unsafe_allow_html=True)

# ==== 拼图预览 + 一键下载按钮 ====
final_collage = make_collage(covers, grid, tile_gap, bg_color, border_color, font_size=48, export_size=1000)
buf = BytesIO()
final_collage.save(buf, format="PNG")
mime = "image/png"
file_ext = "png"
st.image(final_collage, caption=tr("export_btn"), use_container_width=True)

# ==== 合并下载按钮，只保留拼图与列表各一个下载按钮 ====
dl_buttons = st.columns(2)
with dl_buttons[0]:
    st.download_button(
        label=tr("export_btn"),
        data=buf.getvalue(),
        file_name=f"spotify_topsters.{file_ext}",
        mime=mime,
        disabled=st.session_state.get("downloading_collage", False),
        key="collage_download_button",
        help="点击下载拼图"
    )
with dl_buttons[1]:
    st.download_button(
        label=tr("download_list"),
        data=make_list_image(top_items, covers, type_key, theme),
        file_name="spotify_list.png",
        mime="image/png",
        disabled=st.session_state.get("downloading_list", False),
        key="list_download_button",
        help="导出列表为图片"
    )

# ==== 列表展示 & 列表导出（优化版） ====
list_title = {
    "album": tr("list_title_album"),
    "track": tr("list_title_track"),
    "artist": tr("list_title_artist"),
}[type_key]

st.markdown(
    f"""
    <div style='
        text-align:center;
        font-size:1.25em;
        font-weight:700;
        margin:24px 0 12px 0;
        color:{current_theme['text']};
        letter-spacing:1px;
    '>
        {list_title}
    </div>
    """, unsafe_allow_html=True
)

for idx, item in enumerate(top_items, start=1):
    render_list_item(idx, item, type_key, theme)

dl2_key = "downloading_list"
if dl2_key not in st.session_state:
    st.session_state[dl2_key] = False

# ==== 自定义全局CSS美化 ====
st.markdown("""
    <style>
    .stButton>button, .stDownloadButton>button {
        border-radius: 12px !important;
        box-shadow: 0 2px 12px #0002;
        font-weight: 600;
        font-size: 1.08em;
        padding: 0.5em 1em;
        transition: all 0.2s;
        width: 100%;
        margin: 0.5em 0;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background: #1db95422 !important;
        box-shadow: 0 4px 24px #1db95444;
        transform: translateY(-1px);
    }
    .list-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 18px;
        margin-bottom: 6px;
        border-radius: 10px;
        transition: all 0.2s;
    }
    .list-item:hover {
        background: #eafbe5 !important;
        box-shadow: 0 2px 8px #1db95422;
    }
    @media (max-width: 800px) {
        .element-container {max-width: 98vw !important;}
        img {max-width: 90vw !important;}
        .stButton>button {font-size: 0.95em;}
    }
    </style>
""", unsafe_allow_html=True)

st.caption(
    f"<div style='text-align:center;color:{current_theme['text']};opacity:0.7;margin-top:18px;font-size:0.98em;'>{tr('powered')}</div>",
    unsafe_allow_html=True
)
