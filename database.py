import sqlite3
import datetime
import json

DB_FILE = "poem_notes.db"

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 创建解析记录表
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poem_hash TEXT,
                    title TEXT,
                    author TEXT,
                    content TEXT,
                    analysis TEXT,
                    created_at TIMESTAMP
                )''')
    
    # 尝试添加新列（如果不存在）
    # SQLite 不支持 IF NOT EXISTS on ADD COLUMN，所以用 try-except
    try:
        c.execute('ALTER TABLE analysis_history ADD COLUMN user_comment TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute('ALTER TABLE analysis_history ADD COLUMN tags TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute('ALTER TABLE analysis_history ADD COLUMN rating INTEGER')
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def save_analysis(poem, analysis_text):
    """保存解析记录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 获取基本信息
    title = poem.get('title', '无题')
    author = poem.get('author', '佚名')
    
    # 构造内容字符串用于存储
    content_list = poem.get('paragraphs') or poem.get('content') or poem.get('para') or []
    if isinstance(content_list, list):
        content_str = "\n".join([str(x) for x in content_list])
    else:
        content_str = str(content_list)
        
    # 生成哈希用于去重（可选，这里暂不做强制去重，允许重复解析）
    poem_hash = str(hash(content_str))
    
    created_at = datetime.datetime.now()
    
    c.execute('''INSERT INTO analysis_history 
                 (poem_hash, title, author, content, analysis, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (poem_hash, title, author, content_str, analysis_text, created_at))
    
    conn.commit()
    conn.close()

def update_note(record_id, user_comment, tags, rating=None):
    """更新笔记的点评、标签和评分"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''UPDATE analysis_history 
                 SET user_comment = ?, tags = ?, rating = ?
                 WHERE id = ?''', (user_comment, tags, rating, record_id))
    conn.commit()
    conn.close()

def get_history(keyword=None, tag_filter=None):
    """获取历史记录，支持筛选"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问
    c = conn.cursor()
    
    sql = 'SELECT * FROM analysis_history WHERE 1=1'
    params = []
    
    if keyword:
        sql += ' AND (title LIKE ? OR author LIKE ? OR content LIKE ? OR user_comment LIKE ? OR tags LIKE ?)'
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw])
        
    if tag_filter:
        sql += ' AND tags LIKE ?'
        params.append(f"%{tag_filter}%")
        
    sql += ' ORDER BY created_at DESC'
    
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_existing_tags():
    """获取所有已使用的标签"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 检查表是否存在
    try:
        c.execute('SELECT tags FROM analysis_history')
        rows = c.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    
    tags_set = set()
    for row in rows:
        if row[0]:
            # 兼容中英文逗号
            for t in row[0].replace('，', ',').split(','):
                t = t.strip()
                if t:
                    tags_set.add(t)
    return sorted(list(tags_set))

def delete_history(record_id):
    """删除指定记录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM analysis_history WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
