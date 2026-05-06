# WorldPulse AI

## 项目简介

WorldPulse AI 是一个基于 Python 和 AI 的全球事件监控仪表盘。它旨在自动采集全球新闻和公开事件数据，利用 AI 进行中文摘要、事件分类、地理识别、风险评分，并在交互式地图和面板中展示。此外，它还支持一键生成适合社交媒体发布的中文内容。

本项目参考 World Monitor 的产品形态，但独立开发，不复制其源码、UI、品牌名称、文案和商业标识。第一版目标是实现一个轻量级的 MVP，优先保证数据采集、AI 分析、地图展示和社媒文案生成的主流程跑通。

## 功能说明

- **数据采集**: 从配置的 RSS 源自动抓取全球新闻。
- **数据清洗去重**: 根据新闻 URL 或标题哈希进行去重，确保数据唯一性。
- **AI 结构化分析**: 对新闻进行 AI 摘要、事件分类、国家/城市识别、严重程度和风险等级评估，并提取适合社交媒体传播的角度。
- **地理定位**: 根据 AI 识别的国家和城市信息，通过 Nominatim 服务获取经纬度，并进行缓存。
- **地图展示**: 在 Streamlit 仪表盘中通过 Plotly 地图展示全球事件，点的大小反映事件严重程度，悬停显示详细信息。
- **社媒文案生成**: 为单条事件生成微博、小红书和短视频口播风格的中文文案。
- **交互式仪表盘**: 提供时间范围、分类、风险等级、国家和来源筛选功能，以及核心指标卡和 AI 全球简报。

## 安装步骤

1.  **克隆项目**

    ```bash
    git clone <项目仓库地址>
    cd worldpulse-ai
    ```

2.  **创建并激活虚拟环境**

    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**

    ```bash
    pip install -r requirements.txt
    ```

## .env 配置方法

1.  **复制 `.env.example` 文件**

    ```bash
    cp .env.example .env
    ```

2.  **编辑 `.env` 文件**

    打开 `.env` 文件，填入您的 DeepSeek API Key。如果您想使用 Ollama 本地模型，请相应配置。

    ```ini
    DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
    DEEPSEEK_BASE_URL=https://api.deepseek.com
    DEEPSEEK_MODEL=deepseek-chat

    USE_OLLAMA=false
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=qwen2.5:7b
    ```

## 如何运行采集

在 Streamlit 界面中，点击顶部的 "🔄 采集新闻" 按钮即可手动触发 RSS 新闻采集。

## 如何启动 Streamlit

在项目根目录下运行以下命令：

```bash
streamlit run app.py
```

然后通过浏览器访问 Streamlit 提供的本地地址（通常是 `http://localhost:8501`）。

## 如何新增 RSS 源

编辑 `data/sources.yaml` 文件，按照现有格式添加新的 RSS 源信息。例如：

```yaml
sources:
  - name: New News Source
    type: rss
    category: technology
    url: https://example.com/rss.xml
```

保存文件后，重新启动 Streamlit 应用或点击 "🔄 采集新闻" 按钮即可加载新的数据源。

## 项目当前限制

-   第一版不包含用户登录、会员系统、支付系统、权限系统等复杂功能。
-   地图展示仅支持 Plotly 的 `scatter_geo` 或 `scatter_mapbox`，不包含 3D 地球效果。
-   不提供自动发布到社交平台的功能，仅生成文案。
-   不包含复杂爬虫或浏览器自动化功能。
-   界面为中文，不支持多语言切换。
-   不使用向量数据库、RAG、WebSocket 实时推送或 Docker 部署。
