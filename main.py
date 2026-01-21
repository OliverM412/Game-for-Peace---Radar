import os
import json
import time
from datetime import datetime
from duckduckgo_search import DDGS
from openai import OpenAI

# ================= 配置区 =================

# 1. 你想要监控的游戏列表 (可以随时在这里修改)
GAMES = ["王者荣耀", "无畏契约", "蛋仔派对", "KPL", "LPL", "三角洲行动", "英雄联盟"]

# 2. 搜索关键词组合
KEYWORDS = ["联动", "合作", "联名", "新皮肤"]

# 3. 初始化 LLM 客户端 (默认配置为 DeepSeek)
# 如果你使用 OpenAI，请删除 base_url 参数
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"), 
    base_url="https://api.deepseek.com" 
)

# ================= 功能函数 =================

def search_web(game):
    """利用 DuckDuckGo 搜索最近一周的中文新闻"""
    print(f"🔍 正在搜索: {game} ...")
    results = []
    try:
        with DDGS() as ddgs:
            # 搜索指令： "和平精英 (联动 OR 合作 OR 联名)"
            query = f"{game} ({' OR '.join(KEYWORDS)})"
            # region='cn-zh' 限制中文, timelimit='w' 限制过去一周, max_results=8 获取前8条
            search_res = ddgs.text(query, region='cn-zh', timelimit='w', max_results=8)
            if search_res:
                results.extend(search_res)
    except Exception as e:
        print(f"❌ 搜索 {game} 时出错: {e}")
    
    # 稍微暂停一下，避免被搜索引擎判定为机器人
    time.sleep(2)
    return results

def ai_analyze(game, search_results):
    """调用大模型分析搜索结果，提取结构化数据"""
    if not search_results:
        return []

    print(f"🧠 正在分析 {game} 的情报...")
    
    # 将搜索结果拼接成文本喂给 AI
    news_text = ""
    for idx, item in enumerate(search_results):
        news_text += f"{idx+1}. 标题: {item['title']}\n   链接: {item['href']}\n   摘要: {item['body']}\n\n"

    # AI 的提示词 (Prompt)
    prompt = f"""
    你是一个专业的游戏商业情报分析师。请阅读以下关于“{game}”的搜索结果：
    
    {news_text}
    
    任务：从中提取**确切的、官方已确认的**商业化合作或IP联动信息。
    
    要求：
    1. 排除玩家猜测、自制内容或旧闻，只保留最近官宣的活动。
    2. 如果没有发现确切的联动信息，返回空列表 []。
    3. 必须输出为标准的 JSON 格式，不要包含 Markdown 标记（如 ```json）。
    
    JSON 结构示例：
    [
        {{
            "brand": "肯德基",
            "industry": "餐饮",
            "content": "肯德基宅急送联动，推出限定套餐和皮肤",
            "date": "2024-05",
            "source_url": "http://..."
        }}
    ]
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 如果用 OpenAI，请改为 "gpt-4o-mini"
            messages=[
                {"role": "system", "content": "你是一个只输出 JSON 格式的助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # 低创造性，保证事实准确
        )
        content = response.choices[0].message.content.strip()
        
        # 清洗可能存在的 Markdown 格式
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "")
            
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ AI 分析失败: {e}")
        return []

def generate_html(data):
    """生成最终的 HTML 网页"""
    cards_html = ""
    
    if not data:
        cards_html = "<div style='text-align:center; color:#666; padding:50px;'>本周暂无新的商业化联动情报</div>"
    else:
        for item in data:
            # 简单的行业颜色分类
            tag_type = "tag-bd"
            if item['industry'] in ['动漫', '游戏', '影视', '文旅']:
                tag_type = "tag-ip"
                
            cards_html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="game-name">🎮 {item['game']}</span>
                    <span class="date">{item['date']}</span>
                </div>
                <div class="card-body">
                    <div class="row">
                        <span class="brand">{item['brand']}</span>
                        <span class="tag {tag_type}">{item['industry']}</span>
                    </div>
                    <div class="desc">{item['content']}</div>
                </div>
                <div class="card-footer">
                    <a href="{item['source_url']}" target="_blank" class="verify-btn">🔗 点击验证来源</a>
                </div>
            </div>
            """

    # 完整的 HTML 模板 (暗黑电竞风)
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>竞品情报雷达 | Game Radar</title>
        <style>
            :root {{ --bg: #0b0c10; --card-bg: #1f2833; --text-main: #c5c6c7; --highlight: #66fcf1; --gold: #FFD700; --red: #fc5185; }}
            body {{ background-color: var(--bg); color: var(--text-main); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
            h1 {{ text-align: center; color: var(--highlight); margin-bottom: 10px; }}
            .subtitle {{ text-align: center; color: #666; font-size: 14px; margin-bottom: 40px; }}
            
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            
            .card {{ background: var(--card-bg); border-radius: 12px; border: 1px solid #2d3844; overflow: hidden; transition: transform 0.2s; display: flex; flex-direction: column; }}
            .card:hover {{ transform: translateY(-5px); border-color: var(--highlight); }}
            
            .card-header {{ background: rgba(0,0,0,0.2); padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3844; }}
            .game-name {{ color: var(--gold); font-weight: bold; font-size: 14px; }}
            .date {{ font-family: monospace; font-size: 12px; color: #666; }}
            
            .card-body {{ padding: 15px; flex-grow: 1; }}
            .row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
            .brand {{ font-size: 18px; font-weight: 900; color: #fff; }}
            
            .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; color: #fff; font-weight: bold; }}
            .tag-bd {{ background-color: #45a29e; }} /* 商务蓝 */
            .tag-ip {{ background-color: var(--red); }} /* 联动红 */
            
            .desc {{ font-size: 14px; line-height: 1.5; color: #aeb4b9; }}
            
            .card-footer {{ padding: 10px 15px; background: rgba(0,0,0,0.2); border-top: 1px solid #2d3844; text-align: right; }}
            .verify-btn {{ font-size: 12px; color: var(--highlight); text-decoration: none; opacity: 0.8; transition: opacity 0.2s; }}
            .verify-btn:hover {{ opacity: 1; text-decoration: underline; }}
            
            @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <h1>🛡️ 竞品商业化情报雷达</h1>
        <p class="subtitle">更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        
        <div class="grid">
            {cards_html}
        </div>
    </body>
    </html>
    """
    return html_template

# ================= 主程序入口 =================

if __name__ == "__main__":
    all_data = []
    
    # 1. 遍历每个游戏进行搜索和分析
    for game in GAMES:
        # 第一步：搜索
        raw_results = search_web(game)
        
        # 第二步：AI 分析
        if raw_results:
            analyzed_data = ai_analyze(game, raw_results)
            
            # 补充游戏名称到结果中
            for item in analyzed_data:
                item['game'] = game
                all_data.append(item)
    
    # 2. 生成 HTML
    print(f"📊 总计收集到 {len(all_data)} 条有效情报，正在生成页面...")
    html_content = generate_html(all_data)
    
    # 3. 写入文件
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("✅ 任务完成！index.html 已生成。")
