# WorldPulse Trade

## 这是什么

面向跨境电商、外贸、物流团队的全球经营风险雷达。

## 它解决什么问题

每天全球发生大量政策、物流、平台、战争、市场信息，普通新闻网站无法告诉出海经营者“这件事对我有什么影响”。WorldPulse Trade 把这些信息转成中文业务影响分析。

## 适合谁

- 跨境电商卖家
- 外贸业务员
- 物流货代
- 出海创业团队
- 供应链管理人员
- 小型情报/运营团队

## 核心功能

- 全球经营风险地图
- 今日出海风险简报
- 单条事件 AI 深度分析
- 国家/地区影响面板
- 业务风险分类
- 关键词关注
- RSS 数据源扩展
- Demo 数据，一键可演示

## 快速启动

Windows：

```bat
install.bat
start.bat
```

启动后访问：

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

手动启动：

后端：

```bat
uvicorn backend.main:app --reload --port 8000
```

前端：

```bat
cd frontend
npm run dev
```

## 环境变量

项目支持 DeepSeek 或 Ollama，也兼容 OpenAI 环境变量。

DeepSeek 示例：

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Ollama 示例：

```env
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b
```

如果设置了 `OPENAI_API_KEY`，当前 AI 客户端会优先使用 OpenAI SDK 默认配置。

## 当前版本边界

- 不复制 worldmonitor 源码、UI、品牌或文案
- 当前是 MVP，重点是可演示、可运行、可讲清楚价值
- 暂无登录、支付、企业权限
- AI 分析按需触发，避免 token 浪费
- Demo 数据仅用于演示，来源会标记为 Demo Source、Trade Brief Demo 或 Logistics Demo
