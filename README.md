# WorldPulse Radar

## 这是什么

多行业信息面雷达。

## 解决什么问题

很多行业都吃信息面，但普通新闻网站只告诉你发生了什么，不告诉你这件事对你的行业意味着什么。WorldPulse Radar 将全球事件转成不同业务视角的中文影响分析。

## 支持的行业模式

- 总览
- 出海贸易
- 金融市场
- 科技 AI
- 供应链工业
- 地缘安全
- 内容创作

## 核心功能

- 全球事件地图
- 多行业模式切换
- 今日行业简报
- 单条事件行业影响分析
- 国家/地区面板
- 关键词关注
- Demo 数据
- 一键启动

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

```bat
uvicorn backend.main:app --reload --port 8000
cd frontend
npm run dev
```

## 环境变量

DeepSeek：

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Ollama：

```env
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b
```

如果设置了 `OPENAI_API_KEY`，当前 AI 客户端会优先使用 OpenAI SDK 默认配置。

## 当前版本边界

- 当前是 MVP，重点是可演示、可运行、可讲清楚价值
- 暂无登录、支付、会员和企业权限
- 暂无 Docker、WebSocket、3D 地球和复杂企业后台
- AI 分析按需触发，避免 token 浪费
- Demo 数据仅用于演示，不伪装成真实新闻
