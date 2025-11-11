# Veo3 视频生成器

这是一个基于 Streamlit 的简单 Web 界面，用于调用 `https://api.apicore.ai/v1/chat/completions` 接口，复现类 Google Flow 的带图视频生成体验。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

启动后在侧边栏填写 API Token，选择模型并输入提示词/首帧图片即可生成视频。支持流式响应查看任务进度。

## 环境变量
- API Token 需要到 Apicore 控制台获取，格式 `sk-xxxx`。

## 部署
可部署到任何支持 Streamlit 的环境（如 Streamlit Community Cloud、Railway、自建服务器等），只需安装依赖并设置密钥即可。
