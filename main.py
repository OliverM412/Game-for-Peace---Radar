import os
import json
import time
import hashlib
from datetime import datetime
from duckduckgo_search import DDGS
from openai import OpenAI

# ================= 配置区 =================
GAMES = ["和平精英", "王者荣耀", "英雄联盟", "无畏契约", "蛋仔派对", "三角洲行动"]
KEYWORDS = ["联动", "合作", "联名", "新皮肤", "代言"]
DATA_FILE = "data.json"  # 我们的“数据库”文件

client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"), 
    base_url="https://api.deepseek.com"
)

# ================= 辅助函数 =================

def load_history():
    """读取历史数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(data):
    """保存数据回文件"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_id(item):
    """生成唯一ID，用于去重 (游戏+品牌)"""
    # 将 游戏名+品牌名 拼起来做个指纹，避免重复添加同一个合作
    raw = f"{item['game']}_{item['brand']}".lower()
    return hashlib.md5(raw.encode()).hexdigest()

# ================= 搜索与分析 =================

def search_web(game):
    print(f"🔍 正在搜索: {game} ...")
    results = []
    try:
        with DDGS() as ddgs:
            query = f"{game} ({' OR '.join(KEYWORDS)})"
            # 关键修改：timelimit='y' (过去一年)，这样能搜到2025年1月以来的数据
            # 如果想要更久，可以去掉 timelimit 参数，但结果可能太杂
            search_res = ddgs.text(query, region='cn-zh', timelimit='y', max_results=10)
            if search_res:
                results.extend(search_res)
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
    time.sleep(2)
    return results

def ai_analyze(game, search_results):
    if not search_results: return []
    
    news_text = ""
    for idx, item in enumerate(search_results):
        news_text += f"{idx+1}. [{item['title']}] - {item['body']}\n Link: {item['href']}\n\n"

    # 关键修改：在 Prompt 中明确要求从 2025年1月 开始筛选
    prompt = f"""
    你是一个游戏商业情报分析师。请分析关于“{game}”的搜索结果：
    
    {news_text}
    
    任务：提取**从2025年1月至今**的、官方已确认的商业化合作或IP联动信息。
    
    规则：
    1. **时间必须是2025年或2026年**。过滤掉2024年及以前的旧闻。
    2. 忽略玩家猜测，只保留实锤信息。
    3. 输出 JSON 格式：
    [
        {{
            "brand": "品牌名",
            "industry": "行业(如餐饮/动漫/快消)",
            "content": "一句话描述合作内容",
            "date": "上线时间(YYYY-MM)",
            "source_url": "新闻链接"
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except:
        return []

# ================= HTML 生成 (带按月分组) =================
def generate_html(data):
    # 按时间倒序排序
    data.sort(key=lambda x: x.get('date', '0000'), reverse=True)
    
    cards_html = ""
    for item in data:
        tag_type = "tag-ip" if item['industry'] in ['动漫', '游戏', '影视'] else "tag-bd"
        cards_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="game-name">🎮 {item['game']}</span>
                <span class="date">{item['date']}</span>
            </div>
            <div class="card-body">
                <div class="row">
                    <span class="brand" title="{item['brand']}">{item['brand']}</span>
                    <span class="tag {tag_type}">{item['industry']}</span>
                </div>
                <div class="desc">{item['content']}</div>
            </div>
            <div class="card-footer">
                <a href="{item['source_url']}" target="_blank" class="verify-btn">🔗 来源验证</a>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>竞品情报雷达 (历史库版)</title>
        <style>
            :root {{ --bg: #0b0c10; --card: #1f2833; --text: #c5c6c7; --cyan: #66fcf1; --gold: #FFD700; }}
            body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; padding: 20px; }}
            h1 {{ text-align: center; color: var(--cyan); }}
            .stats {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            .card {{ background: var(--card); border: 1px solid #333; border-radius: 8px; overflow: hidden; display:flex; flex-direction:column; }}
            .card:hover {{ border-color: var(--gold); transform: translateY(-3px); transition: 0.3s; }}
            .card-header {{ background: rgba(0,0,0,0.3); padding: 10px 15px; display: flex; justify-content: space-between; font-size: 12px; }}
            .game-name {{ color: var(--gold); font-weight: bold; }}
            .card-body {{ padding: 15px; flex: 1; }}
            .row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
            .brand {{ font-size: 16px; font-weight: bold; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }}
            .tag {{ font-size: 10px; padding: 2px 6px; border-radius: 4px; color: #fff; }}
            .tag-bd {{ background: #45a29e; }} .tag-ip {{ background: #fc5185; }}
            .desc {{ font-size: 13px; color: #999; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
            .card-footer {{ padding: 10px; background: rgba(0,0,0,0.2); text-align: right; }}
            .verify-btn {{ font-size: 12px; color: var(--cyan); text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🛡️ 竞品商业化情报库</h1>
        <div class="stats">
            已收录 2025年1月至今 共 {len(data)} 条情报 • 最后更新: {datetime.now().strftime('%Y-%m-%d')}
        </div>
        <div class="grid">{cards_html}</div>
    </body>
    </html>
    """
    return html

# ================= 主程序 =================
if __name__ == "__main__":
    # 1. 读取旧数据
    history_data = load_history()
    existing_ids = set(generate_id(item) for item in history_data)
    print(f"📚 现有历史数据: {len(history_data)} 条")

    new_items_count = 0
    
    # 2. 搜索并增量更新
    for game in GAMES:
        raw_results = search_web(game)
        if raw_results:
            ai_data = ai_analyze(game, raw_results)
            for item in ai_data:
                item['game'] = game
                # 去重检查
                uid = generate_id(item)
                if uid not in existing_ids:
                    history_data.append(item)
                    existing_ids.add(uid)
                    new_items_count += 1
                    print(f"✅ 新增情报: {item['game']} x {item['brand']}")
                else:
                    print(f"🔄 已存在，跳过: {item['game']} x {item['brand']}")

    # 3. 保存数据 (修改点：如果文件不存在，强制创建，防止 git 报错)
    if new_items_count > 0 or not os.path.exists(DATA_FILE):
        save_history(history_data)
        print(f"💾 数据库已更新/初始化，当前共有 {len(history_data)} 条数据。")
    else:
        print("🤷‍♂️ 本次未发现全新情报，且数据库已存在，跳过写入。")

    # 4. 生成 HTML
    html = generate_html(history_data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("✅ 网页生成完毕。")
