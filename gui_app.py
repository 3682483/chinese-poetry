import streamlit as st
import streamlit.components.v1 as components
import random
import os
import sys
import json
import opencc

# 将当前目录添加到路径中，以便能导入 loader
sys.path.append(os.getcwd())

from loader.data_loader import PlainDataLoader

# 设置页面配置
st.set_page_config(
    page_title="古诗词数据库",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 加载自定义 CSS
st.markdown("""
<style>
    .poem-card {
        background-color: #f9f9f9;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    .poem-title {
        font-size: 2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .poem-author {
        font-size: 1.2rem;
        color: #7f8c8d;
        margin-bottom: 1.5rem;
        font-style: italic;
    }
    .poem-content {
        font-size: 1.4rem;
        line-height: 2;
        color: #34495e;
        font-family: "KaiTi", "SimKai", serif;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_converters():
    return opencc.OpenCC('s2t'), opencc.OpenCC('t2s')

@st.cache_resource
def get_loader():
    """缓存加载器实例，避免重复加载"""
    try:
        return PlainDataLoader()
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

def main():
    loader = get_loader()
    if not loader:
        return

    st.title("📜 中华古诗词数据库")
    st.markdown("探索中国古代文学的瑰宝")

    # 侧边栏
    with st.sidebar:
        st.header("功能菜单")
        
        # 获取所有数据集ID
        dataset_ids = list(loader.id_table.keys())
        # 创建更友好的显示名称映射 (这里只是简单的映射，实际可以更完善)
        dataset_names = {
            "tang-shi": "全唐诗",
            "song-ci": "全宋词",
            "shi-jing": "诗经",
            "chu-ci": "楚辞",
            "lun-yu": "论语",
            # 其他可以保持原样
        }
        
        selected_dataset_id = st.selectbox(
            "选择文集",
            options=["all"] + dataset_ids,
            format_func=lambda x: "📚 所有文集" if x == "all" else f"📖 {dataset_names.get(x, x)}"
        )
        
        mode = st.radio("浏览模式", ["🎲 随机探索", "🔍 搜索查询"])

        st.markdown("---")
        st.markdown("### 关于")
        st.info("本项目包含全唐诗、全宋词、诗经、论语等大量中国古代文学经典。")

    # 主要内容区域
    if mode == "🎲 随机探索":
        show_random_mode(loader, selected_dataset_id)
    else:
        show_search_mode(loader, selected_dataset_id)

def show_random_mode(loader, dataset_id):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎲 换一首", type="primary"):
            st.session_state.random_poem = get_random_poem(loader, dataset_id)

    # 初始化
    if 'random_poem' not in st.session_state:
        st.session_state.random_poem = get_random_poem(loader, dataset_id)
    
    poem = st.session_state.random_poem
    if poem:
        display_poem(poem)

def get_random_poem(loader, dataset_id):
    try:
        if dataset_id == "all":
            # 从所有数据集中随机选一个，然后再取一首
            target = random.choice(list(loader.datasets.keys()))
            poems = loader.get_poems(target)
        else:
            # 获取对应的数据集名称
            target = loader.id_table[dataset_id]
            poems = loader.get_poems(target)
            
        if poems:
            return random.choice(poems)
        return None
    except Exception as e:
        st.error(f"获取诗词出错: {e}")
        return None

def show_search_mode(loader, dataset_id):
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("输入关键词 (标题或作者)", placeholder="例如：李白, 静夜思...")
    with col2:
        search_type = st.selectbox("搜索范围", ["作者", "标题", "内容"])
    
    if query:
        with st.spinner(f"正在搜索 '{query}'..."):
            results = search_poems(loader, dataset_id, query, search_type)
        
        if results:
            st.success(f"找到 {len(results)} 条结果")
            
            # 分页
            page_size = 10
            if len(results) > page_size:
                page = st.slider("页码", 1, (len(results) - 1) // page_size + 1, 1)
                start_idx = (page - 1) * page_size
                current_results = results[start_idx : start_idx + page_size]
            else:
                current_results = results

            for poem in current_results:
                # 兼容不同数据格式的显示标题
                title = poem.get('title', '无题')
                if isinstance(poem.get('content'), list):
                    # 某些数据集如诗经，内容在 content 字段且为列表
                    preview = poem['content'][0]
                elif isinstance(poem.get('paragraphs'), list):
                    preview = poem['paragraphs'][0]
                elif isinstance(poem.get('para'), list):
                    preview = poem['para'][0]
                elif isinstance(poem, dict) and 'content' in poem:
                    content_val = poem['content']
                    if isinstance(content_val, list) and content_val and isinstance(content_val[0], dict):
                        # 字典列表（如弟子规）
                        first_item = content_val[0]
                        paras = first_item.get('paragraphs', []) or first_item.get('content', [])
                        preview_text = paras[0] if paras else "..."
                        preview = f"{first_item.get('chapter', '')} {preview_text}"
                    elif isinstance(content_val, list) and content_val:
                        preview = content_val[0]
                    else:
                        preview = str(content_val)
                else:
                    preview = "点击查看详情"
                    
                if title == '无题' and 'chapter' in poem:
                    title = f"{poem.get('chapter', '')} - {poem.get('section', '')}"
                
                with st.expander(f"{title} - {poem.get('author', '佚名')}"):
                    display_poem(poem, simple=True)
        else:
            st.warning("未找到相关诗词")

def search_poems(loader, dataset_id, query, search_type):
    # 注意：这就只是一个简单的演示搜索，对于大数据集可能会慢
    # 实际应用中应该建立索引
    
    targets = []
    if dataset_id == "all":
        targets = list(loader.datasets.keys())
    else:
        targets = [loader.id_table[dataset_id]]
    
    results = []
    query = query.lower()
    
    # 限制搜索范围以防太慢，这里只搜前几个文件演示，或者限制总数
    # 为了演示效果，我们还是尽量搜，但加上最大结果限制
    MAX_RESULTS = 100
    
    for target in targets:
        if len(results) >= MAX_RESULTS:
            break
            
        # 使用新的 get_poems 方法获取完整对象
        poems = loader.get_poems(target)
        if not poems:
            continue
            
        for poem in poems:
            if len(results) >= MAX_RESULTS:
                break
                
            match = False
            
            # 兼容处理：有些数据集可能没有 title/author 字段，或者字段名不同
            # 例如诗经只有 title, chapter, section, content
            
            if search_type == "作者":
                if query in poem.get('author', '').lower():
                    match = True
            elif search_type == "标题":
                if query in poem.get('title', '').lower():
                    match = True
            elif search_type == "内容":
                # 尝试获取内容，可能是 paragraphs, content 或 para
                content_list = poem.get('paragraphs', [])
                if not content_list:
                    content_list = poem.get('content', [])
                if not content_list:
                    content_list = poem.get('para', [])
                
                if isinstance(content_list, list):
                    if content_list and isinstance(content_list[0], dict):
                         # 字典列表
                         full_str = ""
                         for item in content_list:
                             if isinstance(item, dict):
                                 full_str += item.get('chapter', '')
                                 paras = item.get('paragraphs', []) or item.get('content', [])
                                 if isinstance(paras, list):
                                     full_str += "".join([str(p) for p in paras])
                         content = full_str.lower()
                    else:
                        content = "".join([str(x) for x in content_list]).lower()
                elif isinstance(content_list, str):
                    content = content_list.lower()
                else:
                    content = ""
                    
                if query in content:
                    match = True
            
            if match:
                results.append(poem)
                
    return results

def display_poem(poem, simple=False):
    # 这里的 poem 应该是一个字典对象了
    if not isinstance(poem, dict):
        st.error(f"数据格式错误: {type(poem)}")
        st.text(str(poem))
        return

    # 获取原始内容
    raw_title = poem.get('title', '')
    if not raw_title: raw_title = poem.get('rhythmic', '')
    if not raw_title: raw_title = poem.get('chapter', '无题')
    
    raw_author = poem.get('author', '佚名')
    paragraphs = poem.get('paragraphs', [])
    if not paragraphs:
        paragraphs = poem.get('content', [])
    if not paragraphs:
        paragraphs = poem.get('para', [])
    
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    
    # 简繁转换准备
    s2t, t2s = get_converters()
    
    # 辅助函数：处理内容转换和 HTML 生成
    def process_content(content_data, converter):
        html_parts = []
        text_parts = []
        
        if isinstance(content_data, list):
            # 检查列表内容类型
            if not content_data:
                return "", ""
                
            if isinstance(content_data[0], str):
                # 字符串列表（普通诗词）
                for line in content_data:
                    if isinstance(line, str):
                        converted_line = converter.convert(line)
                        html_parts.append(f'<div>{converted_line}</div>')
                        text_parts.append(converted_line)
            elif isinstance(content_data[0], dict):
                # 字典列表（如弟子规，包含章节）
                for item in content_data:
                    if not isinstance(item, dict): continue
                    
                    # 尝试获取章节标题
                    chap_title = item.get('chapter', '')
                    if chap_title:
                        conv_title = converter.convert(chap_title)
                        html_parts.append(f'<h3 style="margin: 15px 0 10px 0; font-size: 20px;">{conv_title}</h3>')
                        text_parts.append(conv_title)
                    
                    # 尝试获取章节内容
                    chap_paras = item.get('paragraphs', [])
                    if not chap_paras:
                        chap_paras = item.get('content', [])
                        
                    if isinstance(chap_paras, list):
                        for line in chap_paras:
                            if isinstance(line, str):
                                conv_line = converter.convert(line)
                                html_parts.append(f'<div>{conv_line}</div>')
                                text_parts.append(conv_line)
                                
        elif isinstance(content_data, str):
            # 纯字符串
            converted = converter.convert(content_data)
            html_parts.append(f'<div>{converted}</div>')
            text_parts.append(converted)
            
        return "".join(html_parts), "。".join(text_parts)

    # 生成简体版
    sim_title = t2s.convert(raw_title)
    sim_author = t2s.convert(raw_author)
    sim_content_html, sim_full_text = process_content(paragraphs, t2s)
    
    # 生成繁体版
    trad_title = s2t.convert(sim_title)
    trad_author = s2t.convert(sim_author)
    trad_content_html, trad_full_text = process_content(paragraphs, s2t)
    
    # 构造数据对象
    data_sim = json.dumps({
        "title": sim_title,
        "author": sim_author,
        "content_html": sim_content_html,
        "full_text": f"{sim_title}。{sim_author}。{sim_full_text}"
    })
    
    data_trad = json.dumps({
        "title": trad_title,
        "author": trad_author,
        "content_html": trad_content_html,
        "full_text": f"{trad_title}。{trad_author}。{trad_full_text}"
    })
    
    # 计算 iframe 高度 (粗略估计)
    # 简单的行数估计不再准确，这里给一个更大的默认值或基于字符数估计
    content_len = len(sim_full_text)
    estimated_height = 130 + (content_len / 20) * 30 
    if estimated_height < 300: estimated_height = 300
    
    total_height = int(estimated_height)
    if total_height > 600:
        total_height = 600
        scrolling = True
    else:
        scrolling = False

    # HTML 模板
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            font-family: "KaiTi", "SimKai", "Microsoft YaHei", serif;
            text-align: center;
            background-color: {'#ffffff' if simple else '#f9f9f9'};
            padding: 10px;
            margin: 0;
            overflow-y: {'auto' if scrolling else 'hidden'};
        }}
        .poem-card {{
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: {'none' if simple else '0 2px 4px rgba(0,0,0,0.05)'};
        }}
        .header {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 10px;
        }}
        .title {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-right: 10px;
        }}
        .controls {{
            display: flex;
            align-items: center;
        }}
        .btn {{
            cursor: pointer;
            background: none;
            border: none;
            font-size: 24px;
            margin: 0 5px;
            transition: transform 0.2s;
            padding: 0;
            line-height: 1;
        }}
        .play-btn {{ color: #3498db; }}
        .play-btn:hover {{ color: #2980b9; transform: scale(1.1); }}
        .stop-btn {{ color: #e74c3c; }}
        .stop-btn:hover {{ color: #c0392b; transform: scale(1.1); }}
        .font-btn {{ 
            color: #8e44ad; 
            font-size: 16px; 
            border: 1px solid #8e44ad; 
            border-radius: 4px; 
            padding: 2px 6px;
            font-weight: bold;
        }}
        .font-btn:hover {{ background-color: #8e44ad; color: white; }}
        
        .author {{
            font-size: 16px;
            color: #7f8c8d;
            margin-bottom: 20px;
            font-style: italic;
        }}
        .content {{
            font-size: 18px;
            line-height: 2;
            color: #34495e;
        }}
    </style>
    </head>
    <body>
        <div class="poem-card">
            <div class="header">
                <span class="title" id="title">{sim_title}</span>
                <div class="controls">
                    <button class="btn play-btn" onclick="playSpeech()" title="朗读">🔊</button>
                    <button class="btn stop-btn" onclick="stopSpeech()" title="停止">⏹</button>
                    <button class="btn font-btn" onclick="toggleFont()" title="简/繁切换">繁</button>
                </div>
            </div>
            <div class="author" id="author">{sim_author}</div>
            <div class="content" id="content">
                {sim_content_html}
            </div>
        </div>

        <script>
            var dataSim = {data_sim};
            var dataTrad = {data_trad};
            var isTraditional = false;
            var synth = window.speechSynthesis;
            var currentUtterance = null;

            function toggleFont() {{
                isTraditional = !isTraditional;
                var data = isTraditional ? dataTrad : dataSim;
                document.getElementById('title').innerText = data.title;
                document.getElementById('author').innerText = data.author;
                document.getElementById('content').innerHTML = data.content_html;
                document.querySelector('.font-btn').innerText = isTraditional ? '简' : '繁';
            }}

            function playSpeech() {{
                stopSpeech();
                var data = isTraditional ? dataTrad : dataSim;
                var text = data.full_text;
                
                var utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = "zh-CN";
                utterance.rate = 0.9;
                
                // 尝试选择中文语音
                var voices = synth.getVoices();
                var zhVoice = voices.find(v => v.lang.includes('zh') || v.lang.includes('CN'));
                if (zhVoice) {{
                    utterance.voice = zhVoice;
                }}
                
                currentUtterance = utterance;
                synth.speak(utterance);
            }}
            
            function stopSpeech() {{
                if (synth.speaking) {{
                    synth.cancel();
                }}
            }}
            
            // 加载语音列表
            if (speechSynthesis.onvoiceschanged !== undefined) {{
                speechSynthesis.onvoiceschanged = function() {{
                    window.speechSynthesis.getVoices(); 
                }};
            }}
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=total_height, scrolling=scrolling)

if __name__ == "__main__":
    main()
