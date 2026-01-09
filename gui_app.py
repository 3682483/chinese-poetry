import streamlit as st
import streamlit.components.v1 as components
import random
import os
import sys
import json
import database
import opencc
import openai
from dotenv import load_dotenv

# 加载环境变量
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, '.env'))

# 将当前目录添加到路径中，以便能导入 loader
sys.path.append(os.getcwd())

from loader.data_loader import PlainDataLoader

@st.cache_data(show_spinner=False)
def get_ai_analysis(api_key, base_url, model_name, title, author, content):
    """调用 AI API 进行诗词解析"""
    if not api_key:
        return "请先在侧边栏设置 AI API Key"
    
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        
        prompt = f"""
        请解析这首诗词，重点在于如何将其作为作文素材进行引用：
        标题：《{title}》
        作者：{author}
        内容：{content}
        
        请提供以下解析（保持简洁达意）：
        1. **核心意象与情感**：用一句话概括诗歌的核心情感或哲理。
        2. **作文引用角度**：列举2-3个适合引用的作文主题（如“思乡”、“坚韧”、“时光”等），并说明引用理由。
        3. **经典名句赏析**：挑选最经典的一两句进行简要赏析，说明其妙处。
        4. **素材运用示范**：写一段100字左右的示例段落，展示如何在作文中自然地引用这首诗或其中的名句。
        """
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个精通中国古诗词的文学专家，擅长指导学生写作。"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 解析出错: {str(e)}"

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
    # 初始化数据库
    database.init_db()
    
    loader = get_loader()
    if not loader:
        return

    # 注入 CSS 以优化布局，减少顶部空白
    st.markdown("""
        <style>
            .block-container {
                padding-top: 2rem !important;
                padding-bottom: 1rem !important;
            }
            /* 调整标题下方的间距 */
            h1 {
                margin-bottom: 0.5rem !important;
            }
            /* 隐藏顶部默认的 hamburger menu 和 footer (可选) */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            /* header {visibility: hidden;}  <-- 恢复 header 显示，否则侧边栏开关也会消失 */
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📜 中华古诗词数据库")
    st.markdown("探索中国古代文学的瑰宝")

    # 侧边栏
    with st.sidebar:
        st.header("功能菜单")
        
        # 获取所有数据集ID
        dataset_ids = list(loader.id_table.keys())

        if "pending_dataset_selector" in st.session_state:
            st.session_state["dataset_selector"] = st.session_state.pop("pending_dataset_selector")
        
        def get_dataset_display_name(x):
            if x == "all":
                return "📚 所有文集"
            # 获取数据集对应的key
            dataset_key = loader.id_table.get(x)
            if dataset_key and dataset_key in loader.datasets:
                name = loader.datasets[dataset_key].get('name', dataset_key)
                return f"📖 {name}"
            return f"📖 {x}"
        
        selected_dataset_id = st.selectbox(
            "选择文集",
            options=["all"] + dataset_ids,
            format_func=get_dataset_display_name,
            key="dataset_selector"
        )
        
        MODE_RANDOM = "🎲 随机探索"
        MODE_SEARCH = "🔍 搜索查询"
        MODE_GALLERY = "📚 文集画廊"
        MODE_NOTES = "📝 解析笔记"

        mode = st.radio("浏览模式", [MODE_RANDOM, MODE_SEARCH, MODE_GALLERY, MODE_NOTES])

        st.markdown("---")
        st.header("🤖 AI 赏析设置")
        
        # 从环境变量加载默认值
        env_ai_enabled = os.getenv("AI_ENABLED", "False").lower() == "true"
        env_base_url = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
        env_api_key = os.getenv("AI_API_KEY", "")
        env_model_name = os.getenv("AI_MODEL_NAME", "deepseek-chat")
        
        # 使用 session_state 保持状态，如果未初始化则使用环境变量
        if 'ai_enabled' not in st.session_state:
            st.session_state.ai_enabled = env_ai_enabled
        
        ai_enabled = st.checkbox("启用 AI 解析", value=st.session_state.ai_enabled, key="ai_enabled_checkbox")
        # 同步 checkbox 状态到 session_state (Streamlit 的 key 机制有时比较绕，手动同步更稳妥)
        st.session_state.ai_enabled = ai_enabled

        if ai_enabled:
            # 初始化 session state 变量
            st.session_state.setdefault('ai_base_url', env_base_url)
            st.session_state.setdefault('ai_api_key', env_api_key)
            st.session_state.setdefault('ai_model_name', env_model_name)

            st.text_input("API Base URL", key="ai_base_url")
            st.text_input("API Key", type="password", key="ai_api_key")
            st.text_input("模型名称", key="ai_model_name")
            
            if not st.session_state.ai_api_key:
                st.warning("请输入 API Key 以使用 AI 功能")

        st.markdown("---")
        st.markdown("### 关于")
        st.info("本项目包含全唐诗、全宋词、诗经、论语等大量中国古代文学经典。")

    # 主要内容区域
    if mode == MODE_RANDOM:
        show_random_mode(loader, selected_dataset_id)
    elif mode == MODE_SEARCH:
        show_search_mode(loader, selected_dataset_id)
    elif mode == MODE_GALLERY:
        show_gallery_mode(loader, selected_dataset_id)
    else:
        show_notes_mode()

def show_gallery_mode(loader, dataset_id):
    st.header("📚 文集画廊")
    
    # 1. 检查是否选择了具体文集
    if dataset_id == "all":
        st.info("💡 请在左侧侧边栏的【选择文集】下拉框中选择一个具体的文集（如：全唐诗），以开启画廊浏览模式。")
        st.markdown("### 📚 所有文集")
        st.caption("点击下方卡片可直接跳转到对应文集")
        
        cols = st.columns(4)
        for idx, (ds_id, ds_key) in enumerate(loader.id_table.items()):
            name = loader.datasets[ds_key].get('name', ds_key)
            with cols[idx % 4]:
                if st.button(f"📖 {name}", key=f"sel_ds_{ds_id}", use_container_width=True):
                    st.session_state["pending_dataset_selector"] = ds_id
                    st.rerun()
        return

    # 2. 加载数据 (带缓存)
    # 当数据集ID变化时，重新加载
    if 'gallery_dataset' not in st.session_state or st.session_state.gallery_dataset != dataset_id:
        with st.spinner(f"正在加载文集数据，请稍候..."):
            target = loader.id_table[dataset_id]
            st.session_state.gallery_poems = loader.get_poems(target)
            st.session_state.gallery_dataset = dataset_id
            st.session_state.gallery_page = 1
            st.session_state.gallery_view_mode = 'grid' # 重置为网格视图
            
    poems = st.session_state.gallery_poems
    if not poems:
        st.warning("该文集暂无数据。")
        return

    # 3. 视图控制 (列表 vs 详情)
    if 'gallery_view_mode' not in st.session_state:
        st.session_state.gallery_view_mode = 'grid'

    if st.session_state.gallery_view_mode == 'detail':
        # 详情模式
        col_back, col_title = st.columns([1, 5])
        with col_back:
            if st.button("🔙 返回画廊", type="secondary"):
                st.session_state.gallery_view_mode = 'grid'
                st.rerun()
        
        selected_poem = st.session_state.get('gallery_selected_poem')
        if selected_poem:
            display_poem(selected_poem, unique_id="gallery_detail")
        else:
            st.error("未选择诗词")
            
    else:
        # 网格模式
        # 分页配置
        page_size = 24 # 4列 * 6行
        total_items = len(poems)
        total_pages = (total_items - 1) // page_size + 1
        
        # 顶部控制栏
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.caption(f"当前文集共 {total_items} 首")
        with c3:
            # 只有页数大于1才显示
            if total_pages > 1:
                current_page = st.number_input(
                    f"页码 (共{total_pages}页)", 
                    min_value=1, 
                    max_value=total_pages, 
                    value=st.session_state.gallery_page,
                    key="gallery_page_input"
                )
                # 更新页码状态
                if current_page != st.session_state.gallery_page:
                    st.session_state.gallery_page = current_page
                    st.rerun()
            else:
                current_page = 1

        # 切片数据
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)
        page_poems = poems[start_idx:end_idx]
        
        # 渲染网格
        cols = st.columns(4) # 4列布局
        
        # 自定义 CSS 让按钮像卡片一样
        st.markdown("""
        <style>
        /* 针对 Streamlit 按钮的自定义样式，使其更像卡片 */
        div.stButton > button {
            width: 100%;
            height: auto !important;
            min_height: 140px;
            white-space: pre-wrap !important;
            line-height: 1.6;
            padding: 12px 12px !important;
            text-align: left;
            display: block;  /* 使用 block 以支持 first-line */
            background-color: #fcfcfc; /* 极浅的灰色背景 */
            border: 1px solid #eeeeee;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            transition: all 0.3s ease;
            color: #555;
            font-family: "Serif", "KaiTi", "SimKai", sans-serif; /* 尝试使用衬线体或楷体 */
        }
        
        /* 悬停效果 */
        div.stButton > button:hover {
            border-color: #d0d0d0;
            box-shadow: 0 6px 12px rgba(0,0,0,0.08);
            background-color: #ffffff;
            transform: translateY(-3px);
            color: #333;
        }

        /* 针对首行（标题）的特殊样式 */
        div.stButton > button p:first-child::first-line, 
        div.stButton > button::first-line {
            font-size: 1.1em;
            /* font-weight: bold;  <-- 移除粗体，改为在文本中使用 Markdown 控制 */
            color: #2c3e50;
            line-height: 1.8;
        }
        </style>
        """, unsafe_allow_html=True)

        for i, poem in enumerate(page_poems):
            with cols[i % 4]:
                title = poem.get('title', '无题')
                author = poem.get('author', '佚名')
                
                # 获取预览文字
                content_list = poem.get('paragraphs') or poem.get('content') or []
                preview = ""
                if isinstance(content_list, list) and content_list:
                    # 取前4句，构建更丰富的预览
                    lines = content_list[:4]
                    formatted_lines = []
                    for line in lines:
                        s_line = str(line)
                        # 如果单行太长，适当截断以保持整洁
                        if len(s_line) > 18:
                            s_line = s_line[:18] + "..."
                        formatted_lines.append(s_line)
                    
                    preview = "\n".join(formatted_lines)
                    if len(content_list) > 4:
                        preview += "\n..."
                elif isinstance(content_list, str):
                    preview = content_list[:50] + "..." if len(content_list) > 50 else content_list
                
                # 按钮显示内容 - 使用 Markdown 语法
                # 构造更有层次感的文本结构
                # 第一行：**标题** (粗体) + 作者 (正常)
                # 空行
                # 内容 (3-4行)
                label = f"**{title}**  [{author}]\n\n{preview}"
                
                if st.button(label, key=f"gal_btn_{start_idx + i}", use_container_width=True):
                    st.session_state.gallery_selected_poem = poem
                    st.session_state.gallery_view_mode = 'detail'
                    st.rerun()

def show_notes_mode():
    st.header("📝 我的解析笔记")
    
    # 筛选区域
    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        search_kw = st.text_input("🔍 搜索笔记 (标题/作者/内容/点评/标签)", placeholder="输入关键词...")
    with col_filter2:
        existing_tags = database.get_all_existing_tags()
        selected_tag = st.selectbox("🏷️ 按标签筛选", ["全部"] + existing_tags)
    
    tag_filter = selected_tag if selected_tag != "全部" else None
    rows = database.get_history(keyword=search_kw, tag_filter=tag_filter)
    
    if not rows:
        st.info("没有找到匹配的解析记录。")
        return
        
    st.caption(f"共找到 {len(rows)} 条笔记")
        
    for row in rows:
        # row keys: id, title, author, content, analysis, created_at, user_comment, tags
        title = row['title']
        author = row['author']
        # 格式化时间，去掉秒后面的部分
        try:
            time_str = str(row['created_at'])[:16]
        except:
            time_str = str(row['created_at'])
        
        # 准备标签显示
        tags_str = row['tags'] if 'tags' in row.keys() and row['tags'] else ""
        tags_display = f"🏷️ {tags_str}" if tags_str else ""
        
        # 准备点评预览
        comment_preview = ""
        if 'user_comment' in row.keys() and row['user_comment']:
            comment_preview = f"💬 {row['user_comment'][:20]}..."

        # 准备评分显示
        rating_val = row['rating'] if 'rating' in row.keys() and row['rating'] else 0
        rating_display = "⭐" * rating_val if rating_val > 0 else ""

        expander_title = f"{time_str} | {title} - {author} {rating_display} {tags_display} {comment_preview}"
        
        # 如果有搜索关键词或标签筛选，默认展开以便快速查看
        default_expanded = bool(search_kw or tag_filter)
        
        with st.expander(expander_title, expanded=default_expanded):
            # 构造一个符合 display_poem 要求的 poem 对象
            # 注意：数据库中 content 是字符串，可能需要转为 list 以兼容 process_content 的部分逻辑
            # 但 process_content 也支持 string
            poem_obj = {
                'title': title,
                'author': author,
                'content': row['content'].split('\n') if row['content'] else []
            }
            
            # 使用 display_poem 显示诗歌 (左侧)
            # 为了避免重复显示 AI 解析按钮和逻辑，我们需要微调 display_poem 或 
            # 简单地，我们可以只利用 display_poem 的 HTML 生成部分
            # 但重构 display_poem 动作较大。
            # 我们可以给 display_poem 加一个参数 show_ai_ui=False
            
            col_content, col_analysis = st.columns(2)
            
            with col_content:
                # 调用 display_poem，但不显示 AI 部分，只显示卡片
                display_poem(poem_obj, simple=True, unique_id=f"note_{row['id']}", show_ai_ui=False)
            
            with col_analysis:
                st.markdown("#### 🤖 AI 解析")
                st.info(row['analysis'])
            
            st.markdown("---")
            st.markdown("#### ✏️ 个人笔记")
            
            # 评分组件
            curr_rating = row['rating'] if 'rating' in row.keys() and row['rating'] else 0
            rating_options = [0, 1, 2, 3, 4, 5]
            rating_labels = ["未评分", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
            try:
                rating_idx = rating_options.index(curr_rating)
            except:
                rating_idx = 0
            
            new_rating = st.radio(
                "评分", 
                rating_options, 
                index=rating_idx, 
                format_func=lambda x: rating_labels[x], 
                horizontal=True, 
                key=f"rating_{row['id']}"
            )

            c1, c2 = st.columns([3, 2])
            with c1:
                curr_comment = row['user_comment'] if 'user_comment' in row.keys() and row['user_comment'] else ""
                new_comment = st.text_area("个人点评", value=curr_comment, height=150, key=f"comment_{row['id']}")
            
            with c2:
                # 标签部分的 Session State 管理
                tags_key = f"tags_input_{row['id']}"
                curr_tags = row['tags'] if 'tags' in row.keys() and row['tags'] else ""
                
                if tags_key not in st.session_state:
                    st.session_state[tags_key] = curr_tags
                
                st.write("常用标签 (点击添加):")
                qt_cols = st.columns(3)
                quick_tags = ["必背", "伤感", "写景", "咏史", "哲理", "爱情"]
                for i, qt in enumerate(quick_tags):
                    col_idx = i % 3
                    if qt_cols[col_idx].button(qt, key=f"qt_{row['id']}_{i}", use_container_width=True):
                        current_val = st.session_state[tags_key]
                        if current_val:
                            # 简单的去重检查
                            if qt not in current_val:
                                st.session_state[tags_key] = current_val + ", " + qt
                        else:
                            st.session_state[tags_key] = qt
                        st.rerun()
                
                new_tags = st.text_input("标签 (逗号分隔)", key=tags_key, placeholder="如: 伤感, 咏月")
            
            col_save, col_del = st.columns([1, 4])
            with col_save:
                if st.button("💾 保存笔记", key=f"save_note_{row['id']}", type="primary"):
                    database.update_note(row['id'], new_comment, new_tags, new_rating)
                    st.success("笔记已更新")
                    st.rerun()
            
            with col_del:
                if st.button("🗑️ 删除此条记录", key=f"del_note_{row['id']}"):
                    database.delete_history(row['id'])
                    st.rerun()

def show_random_mode(loader, dataset_id):
    ai_enabled = st.session_state.get('ai_enabled', False)
    
    if ai_enabled:
        # AI模式下使用全宽布局，以便容纳左右分栏
        if st.button("🎲 换一首", type="primary", use_container_width=True):
            st.session_state.random_poem = get_random_poem(loader, dataset_id)
            
        if 'random_poem' not in st.session_state:
            st.session_state.random_poem = get_random_poem(loader, dataset_id)
        
        poem = st.session_state.random_poem
        if poem:
            display_poem(poem, unique_id="random")
    else:
        # 普通模式保持居中布局
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🎲 换一首", type="primary"):
                st.session_state.random_poem = get_random_poem(loader, dataset_id)

            # 初始化
            if 'random_poem' not in st.session_state:
                st.session_state.random_poem = get_random_poem(loader, dataset_id)
            
            poem = st.session_state.random_poem
            if poem:
                display_poem(poem, unique_id="random")

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
    query = st.text_input("输入关键词 (全局搜索)", placeholder="例如：李白, 静夜思, 月亮...")
    
    with st.expander("🛠️ 高级筛选 & 设置", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            filter_author = st.text_input("筛选作者 (包含)", placeholder="如: 李白")
        with c2:
            filter_title = st.text_input("筛选标题 (包含)", placeholder="如: 静夜思")
        with c3:
            search_limit = st.number_input("最大结果数", min_value=100, max_value=50000, value=2000, step=1000)

    # 初始化搜索状态
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_page' not in st.session_state:
        st.session_state.search_page = 1
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    
    # 组合缓存键
    current_key = f"{query}_{dataset_id}_{filter_author}_{filter_title}_{search_limit}"

    if query or filter_author or filter_title:
        # 如果查询条件改变，执行新搜索
        if current_key != st.session_state.last_query:
            # Display what is being searched
            search_info = []
            if query: search_info.append(f"关键词: {query}")
            if filter_author: search_info.append(f"作者: {filter_author}")
            if filter_title: search_info.append(f"标题: {filter_title}")
            
            with st.spinner(f"正在搜索 ({', '.join(search_info)})..."):
                results = search_poems(loader, dataset_id, query, filter_author, filter_title, search_limit)
                st.session_state.search_results = results
                st.session_state.last_query = current_key
                st.session_state.search_page = 1
        
        results = st.session_state.search_results
        
        if results:
            st.success(f"找到 {len(results)} 条结果")
            
            # 分页配置
            page_size = 20
            total_items = len(results)
            total_pages = (total_items - 1) // page_size + 1
            
            # 分页控件
            if total_pages > 1:
                col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                with col_p2:
                    st.number_input(
                        f"页码 (共 {total_pages} 页)", 
                        min_value=1, 
                        max_value=total_pages, 
                        step=1,
                        key="search_page"
                    )
            
            # 计算当前页数据
            current_page = st.session_state.search_page
            # 防止溢出
            if current_page > total_pages: current_page = total_pages
            
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_items)
            current_results = results[start_idx : end_idx]
            
            st.caption(f"显示第 {start_idx + 1} - {end_idx} 条")

            for idx, poem in enumerate(current_results):
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
                    display_poem(poem, simple=True, unique_id=f"search_{idx}")
        else:
            st.warning("未找到相关诗词")

def search_poems(loader, dataset_id, query, filter_author=None, filter_title=None, limit=2000):
    # 注意：这就只是一个简单的演示搜索，对于大数据集可能会慢
    # 实际应用中应该建立索引
    
    targets = []
    if dataset_id == "all":
        targets = list(loader.datasets.keys())
    else:
        targets = [loader.id_table[dataset_id]]
    
    results = []
    
    # 准备简繁体多重搜索关键词
    query_variants = set()
    if query:
        s2t, t2s = get_converters()
        # 原始查询、转繁体、转简体，去重
        query_variants = {query, s2t.convert(query), t2s.convert(query)}
        # 转小写并过滤空值
        query_variants = {q.lower() for q in query_variants if q}
    
    def extract_text_recursive(data):
        """递归提取所有文本内容用于搜索"""
        text = ""
        if isinstance(data, dict):
            # 提取可能的文本字段
            for key in ['title', 'author', 'chapter', 'section', 'rhythmic']:
                val = data.get(key)
                if isinstance(val, str):
                    text += val + " "
            
            # 递归处理内容字段
            for key in ['paragraphs', 'content', 'para']:
                val = data.get(key)
                if val:
                    text += extract_text_recursive(val) + " "
        elif isinstance(data, list):
            for item in data:
                text += extract_text_recursive(item) + " "
        elif isinstance(data, str):
            text += data + " "
        elif isinstance(data, (int, float)):
            text += str(data) + " "
            
        return text

    for target in targets:
        if len(results) >= limit:
            break
            
        # 使用新的 get_poems 方法获取完整对象
        poems = loader.get_poems(target)
        if not poems:
            continue
            
        for poem in poems:
            if len(results) >= limit:
                break
            
            # 1. 高级筛选 (AND 逻辑)
            if filter_author:
                poem_author = poem.get('author', '')
                if not poem_author or filter_author not in poem_author:
                    continue
            
            if filter_title:
                poem_title = poem.get('title', '')
                if not poem_title or filter_title not in poem_title:
                    continue

            # 2. 关键词匹配
            match = False
            if not query:
                # 如果没有关键词，但通过了高级筛选，则视为匹配
                match = True
            else:
                # 默认全字段搜索 (包含标题、作者、内容)
                # 使用递归提取全文进行搜索
                full_content = extract_text_recursive(poem).lower()
                if any(q in full_content for q in query_variants):
                    match = True
            
            if match:
                results.append(poem)
                
    return results

def display_poem(poem, simple=False, unique_id=None, show_ai_ui=True):
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
    
    # 统一获取内容入口
    paragraphs = poem.get('paragraphs', [])
    if not paragraphs:
        paragraphs = poem.get('content', [])
    if not paragraphs:
        paragraphs = poem.get('para', [])
    
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    
    # 简繁转换准备
    s2t, t2s = get_converters()
    
    # 辅助函数：递归处理内容转换和 HTML 生成
    def process_content(content_data, converter, level=0):
        html_parts = []
        text_parts = []
        
        if not content_data:
            return "", ""
            
        if isinstance(content_data, list):
            if not content_data:
                return "", ""
                
            first_item = content_data[0]
            
            if isinstance(first_item, str):
                # 字符串列表（最底层内容）
                for line in content_data:
                    if isinstance(line, str):
                        converted_line = converter.convert(line)
                        html_parts.append(f'<div>{converted_line}</div>')
                        text_parts.append(converted_line)
                        
            elif isinstance(first_item, dict):
                # 字典列表（嵌套章节/卷）
                for item in content_data:
                    if not isinstance(item, dict): continue
                    
                    # 尝试获取章节标题
                    # 优先级：chapter > title > section
                    chap_title = item.get('chapter') or item.get('title') or item.get('section') or ''
                    
                    if chap_title:
                        conv_title = converter.convert(chap_title)
                        # 根据层级调整标题样式，避免全是 h3
                        font_size = max(16, 20 - level * 2)
                        margin_top = 15 if level == 0 else 10
                        html_parts.append(f'<h3 style="margin: {margin_top}px 0 10px 0; font-size: {font_size}px;">{conv_title}</h3>')
                        text_parts.append(conv_title)
                    
                    # 递归获取下级内容
                    sub_content = item.get('paragraphs') or item.get('content') or item.get('para') or []
                    
                    sub_html, sub_text = process_content(sub_content, converter, level + 1)
                    html_parts.append(sub_html)
                    if sub_text:
                        text_parts.append(sub_text)
                        
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
    # 增加基础高度，并稍微放宽每行的估算
    estimated_height = 200 + (content_len / 20) * 35 
    if estimated_height < 300: estimated_height = 300
    
    total_height = int(estimated_height)
    # 设置最大高度，超过则滚动
    if total_height > 600:
        total_height = 600
    
    # 始终启用滚动，防止估算错误导致内容被截断
    scrolling = True

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
            overflow-y: auto;  /* 始终允许滚动 */
        }}
        /* 隐藏滚动条但保留功能 (可选，这里为了用户体验保留默认滚动条) */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #f1f1f1; 
        }}
        ::-webkit-scrollbar-thumb {{
            background: #888; 
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #555; 
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
    
    ai_enabled = st.session_state.get('ai_enabled', False)
    
    # 只有当 AI 开启 且 允许显示 AI UI 时才分栏显示
    if ai_enabled and show_ai_ui:
        col_poem, col_ai = st.columns([1.2, 1])
        with col_poem:
            components.html(html_content, height=total_height, scrolling=scrolling)
        
        with col_ai:
            st.markdown("### 🤖 深度解析")
            # 使用内容哈希作为唯一ID用于存储
            poem_id = hash(sim_full_text)
            storage_key = f"analysis_{poem_id}"
            
            # 使用 unique_id 来确保按钮 key 唯一
            btn_key_suffix = unique_id if unique_id is not None else poem_id
            
            # 检查是否已有解析结果
            has_analysis = storage_key in st.session_state
            
            if not has_analysis:
                if st.button("📝 点击一键生成精彩解析", key=f"ai_btn_{btn_key_suffix}"):
                     with st.spinner("正在请求进行深度解析..."):
                         analysis = get_ai_analysis(
                             st.session_state.get('ai_api_key'),
                             st.session_state.get('ai_base_url', 'https://api.deepseek.com'),
                             st.session_state.get('ai_model_name', 'deepseek-chat'),
                             sim_title,
                             sim_author,
                             sim_full_text
                         )
                         st.session_state[storage_key] = analysis
                         
                         # 自动保存到数据库
                         try:
                             database.save_analysis(poem, analysis)
                             st.toast("✅ 解析已自动保存到笔记")
                         except Exception as e:
                             st.error(f"保存笔记失败: {e}")
                             
                         st.rerun()
            
            if storage_key in st.session_state:
                st.info(st.session_state[storage_key])
                if st.button("🗑️ 清除解析", key=f"ai_clear_{btn_key_suffix}"):
                    del st.session_state[storage_key]
                    st.rerun()
    else:
        # 否则只显示诗词卡片 (AI 未开启 或 显式不显示 AI UI)
        components.html(html_content, height=total_height, scrolling=scrolling) 


if __name__ == "__main__":
    main()
