def get_industry_analysis_prompt(industry_config):
    industry_id = industry_config.get("id", "overview")
    industry_name = industry_config.get("name_zh", "总览")
    description = industry_config.get("description", "综合全球重要事件。")
    risk_focus = industry_config.get("risk_focus", "综合重要性和外溢风险。")
    analysis_focus = industry_config.get("analysis_focus", "说明事件为什么重要。")
    actions = industry_config.get("suggested_actions", "关注后续确认信息。")
    categories = " / ".join(industry_config.get("categories", []))
    finance_notice = "金融市场模式必须在 suggested_action 或 market_impact 中提示：不构成投资建议。" if industry_id == "finance" else ""
    return f"""
你是 WorldPulse Radar 的行业信息面分析助手。
当前行业模式：{industry_name} ({industry_id})
行业用途：{description}
重点关注：{risk_focus}
分析重点：{analysis_focus}
建议动作参考：{actions}
可用中文分类参考：{categories}
{finance_notice}

请根据输入新闻，输出严格 JSON，不要输出 Markdown，不要输出解释。

要求：
1. 不能编造事实，只能基于标题、摘要、来源和已知文本做保守判断。
2. 同一事件要按当前行业视角解释，说明它对这个行业意味着什么。
2.1 所有解释类字段必须使用简体中文输出，不得使用英文整句。
3. 如果无法判断国家/城市，country/city 置空，location_scope 用 global/region/unknown。
4. business_impact 说明对业务、经营、供应链、组织决策的影响。
5. market_impact 说明对价格、资产、成本、需求或市场情绪的影响；没有就写空字符串。
6. opportunity_signal 说明是否有选题、采购、产品、投资观察或运营机会；没有就写空字符串。
7. suggested_action 给出实际建议，不要给确定性投资建议。
8. content_angle 给适合内容创作或内部汇报的角度。
9. affected_groups 必须是数组。
10. 除 `country`、`city`、`industry` 外，其他文本字段必须是中文。

输出格式：
{{
  "ai_summary": "",
  "industry": "{industry_id}",
  "category": "",
  "country": "",
  "city": "",
  "severity": 1,
  "confidence": 0.8,
  "risk_level": "low",
  "affected_groups": [],
  "business_impact": "",
  "market_impact": "",
  "opportunity_signal": "",
  "suggested_action": "",
  "content_angle": "",
  "location_scope": "country/city/region/global/unknown",
  "location_confidence": 0.8,
  "location_reason": ""
}}
"""


NEWS_ANALYSIS_PROMPT = """
你是 WorldPulse Radar 的业务风险分析助手，默认按“出海贸易”视角分析。
请根据输入新闻，输出严格 JSON，不要输出 Markdown，不要输出解释。

你需要完成：
1. 用中文总结新闻，80字以内
2. 判断业务风险分类 (tariff_policy/customs_clearance/logistics_delay/port_disruption/platform_policy/sanctions_conflict/currency_oil/supply_chain/market_demand/compliance/other)
3. 判断新闻对应的“主要事件发生地”，而不是媒体所在地、公司总部、受影响市场、泛泛提到的国家
4. 提取国家和城市时必须保守：只有标题或摘要明确指向具体发生地时才填写
5. 国家和城市使用英文标准名称，便于地理编码，例如 "United States"、"New York"；没有明确城市则为空
6. 如果是全球性、跨国、区域性、线上、市场综述、无明确地点的新闻，location_scope 必须为 "global"、"regional"、"online" 或 "unclear"，country/city 置空
7. location_confidence 表示地点判断置信度，0-1；低于 0.55 时 country/city 置空
8. 评估严重程度 1-5 (1=很低, 2=低, 3=中等, 4=高, 5=极高)
9. 给出整体分析置信度 0-1
10. 给出风险等级 (low/medium/high/critical)
11. affected_groups 必须是数组，选择或补充可能受影响对象，例如“跨境电商卖家”“外贸企业”“物流货代”“海外仓团队”“供应链采购”“品牌出海团队”
12. business_impact 要讲清楚“对生意有什么影响”，例如清关成本、履约时效、广告投放、利润率、库存、平台合规、回款与汇率风险
13. suggested_action 要给实际建议，例如检查物流渠道、复核 HS Code、关注平台公告、重新计算利润、暂缓投放广告、调整备货、检查制裁名单
14. 给出适合运营团队转述的 social_angle
15. 除 `country`、`city` 外，所有文本字段必须使用简体中文，不得输出英文整句

地点判断规则：
- 冲突、灾害、抗议、公共卫生、政策事件：用事件实际发生地
- 公司财报、股价、产品发布、AI 模型发布：通常不要按公司总部落点，除非新闻明确说某地发生实体事件
- 国际会议：用会议举办城市
- 多国事件：如果没有单一主要地点，country/city 置空，location_scope="regional" 或 "global"
- 只出现来源媒体国家、机构总部、交易所所在地，不代表事件发生地

输出格式：
{
  "ai_summary": "",
  "category": "",
  "country": "",
  "city": "",
  "severity": 1,
  "confidence": 0.8,
  "risk_level": "low",
  "affected_groups": ["跨境电商卖家", "外贸企业", "物流货代"],
  "business_impact": "",
  "suggested_action": "",
  "social_angle": "",
  "location_scope": "country/city/region/global/unknown",
  "location_confidence": 0.8,
  "location_reason": ""
}
"""

LOCATION_TAGGING_PROMPT = """
你是 WorldPulse Trade 的轻量地图标记助手。
请根据输入新闻，只判断它是否适合放到地图上，并输出严格 JSON，不要 Markdown，不要解释。

目标：
1. 找出新闻的主要事件发生地，不要使用媒体所在地、公司总部、交易所所在地来凑位置
2. 只做地图定位和业务风险粗分类，不要写长摘要，不要做深度 AI 分析
3. 国家和城市使用英文标准名称，便于地理编码
4. 如果没有明确单一发生地，country/city 置空，location_scope 用 global/regional/online/unclear
5. 只有明确地点才用 location_scope="specific"
6. location_confidence 低于 0.55 时 country/city 必须置空

输出格式：
{
  "category": "tariff_policy/customs_clearance/logistics_delay/port_disruption/platform_policy/sanctions_conflict/currency_oil/supply_chain/market_demand/compliance/other",
  "country": "",
  "city": "",
  "location_scope": "specific",
  "location_confidence": 0.8,
  "location_reason": "",
  "severity": 1,
  "risk_level": "low"
}
"""

SOCIAL_WRITER_PROMPT = """
你是一个资深社媒运营专家。请根据以下新闻内容，生成三种风格的文案。
要求：
- 必须基于原新闻和 AI 摘要生成
- 不能编造没有的信息
- 需要提示“内容仅供信息整理，不构成投资建议”

新闻标题: {title}
AI 摘要: {summary}
来源: {source}

请输出 JSON 格式：
{{
  "weibo": "微博风格：150-250字，直接、信息密度高",
  "xiaohongshu": "小红书风格：包含标题、正文、3-5个标签，语气通俗",
  "video_script": "短视频口播风格：30-60秒，开头吸引人，中间解释，结尾引导"
}}
"""

USER_PROFILE_PROMPT = """
你是 WorldPulse Radar 的用户画像分析助手。
请根据用户输入的职业、业务、需求或关注点，生成用于信息面风险筛选的结构化画像。
输出严格 JSON，不要 Markdown，不要解释。

要求：
1. 不要臆造用户没有表达的具体公司、资产、订单或国家。
2. 可以基于职业/需求推断合理的风险关注方向，但 confidence 不要过高。
3. keywords 用于匹配新闻标题和摘要，包含中英文常见词。
4. preferred_categories 必须从以下枚举中选择：
tariff_policy/customs_clearance/logistics_delay/port_disruption/platform_policy/sanctions_conflict/currency_oil/supply_chain/market_demand/compliance/central_bank/commodity_price/stock_market/crypto_market/ai_model/chips/cloud_datacenter/tech_regulation/factory_disruption/raw_materials/energy_supply/military_conflict/diplomacy/protest_unrest/viral_topic/other
5. industries 必须从 overview/trade/finance/tech/supply_chain/geopolitics/content 中选择。
6. countries、platforms、products 如果用户未明确提到，可为空数组。
7. relevance_rules 用中文写 3-5 条，说明哪些事件应优先展示。

输出格式：
{
  "profile_name": "",
  "summary": "",
  "industries": [],
  "preferred_categories": [],
  "keywords": [],
  "countries": [],
  "platforms": [],
  "products": [],
  "risk_focus": [],
  "relevance_rules": [],
  "confidence": 0.7
}
"""
