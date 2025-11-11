import json
import re
from typing import Dict, List, Optional

import requests
from requests import Response
import streamlit as st


API_HOST = "https://api.apicore.ai"
API_PATH = "/v1/chat/completions"

MODEL_OPTIONS = [
    ("veo3", "veo3 · 标准模式 · 画质与速度平衡"),
    ("veo3-fast", "veo3-fast · 快速模式 · 适合迭代"),
    ("veo3-pro", "veo3-pro · 高画质模式 · 产出更细腻"),
    ("veo3-frames", "veo3-frames · 高画质模式 · 支持首帧上传"),
    ("veo3-fast-frames", "veo3-fast-frames · 快速 + 首帧上传"),
    ("veo3-pro-frames", "veo3-pro-frames · 高画质 + 首帧上传"),
]


def build_payload(
    model: str,
    text_prompt: str,
    start_image_url: Optional[str],
    extra_instructions: Optional[str],
    stream: bool,
) -> Dict:
    content: List[Dict] = []

    if text_prompt:
        content.append(
            {
                "type": "text",
                "text": text_prompt.strip(),
            }
        )

    if start_image_url:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": start_image_url.strip(),
                },
                "name": "start_frame",
            }
        )

    if extra_instructions:
        content.append(
            {
                "type": "text",
                "text": extra_instructions.strip(),
            }
        )

    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content or [{"type": "text", "text": "请生成视频"}],
            }
        ],
        "stream": stream,
    }


def send_request(token: str, payload: Dict, stream_mode: bool) -> Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return requests.post(
        f"{API_HOST}{API_PATH}",
        headers=headers,
        data=json.dumps(payload),
        stream=stream_mode,
        timeout=120,
    )


def validate_image_url(image_url: str, label: str = "首帧图片") -> Optional[str]:
    try:
        res = requests.head(
            image_url,
            allow_redirects=True,
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        return f"无法访问首帧图片：{exc}"

    content_type = res.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        return (
            f"{label}地址返回的 Content-Type 不是 image/*，"
            f"当前为 `{content_type or '未知'}`。请使用真实图片直链，比如 GitHub 原图 `raw.githubusercontent.com` 地址。"
        )
    return None


def normalize_stream_text(text: str) -> str:
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeDecodeError:
        return text


def extract_first_url(text: str) -> Optional[str]:
    urls = re.findall(r"https?://[^\s]+", text)
    return urls[0] if urls else None


def main() -> None:
    st.set_page_config(
        page_title="Veo3 视频生成 Demo",
        page_icon="🎬",
        layout="centered",
    )

    st.title("🎬 Veo3 视频生成器")
    st.caption("填写提示词与首帧图 URL，调用 `api.apicore.ai` 生成视频。目前仅支持 Veo3 模型。暂不支持尾帧。")

    with st.sidebar:
        st.header("基础配置")
        token = st.text_input(
            label="API Token（必填）",
            type="password",
            help="在 Apicore 控制台创建的密钥，形如 `sk-xxxx`。",
        )
        selected_model = st.selectbox(
            label="模型选择",
            options=[m[0] for m in MODEL_OPTIONS],
            format_func=lambda value: next(
                (label for model, label in MODEL_OPTIONS if model == value), value
            ),
            index=1,
        )
        stream = st.toggle("开启流式返回（stream）", value=False)

    st.subheader("生成参数")
    col_prompt, col_extra = st.columns(2)
    with col_prompt:
        text_prompt = st.text_area(
            label="视频提示词（支持自然语言 + 比例描述）",
            placeholder="例如：热闹城市夜景，航拍视角，9:16 竖屏",
            height=160,
        )

    with col_extra:
        image_url = st.text_input(
            label="首帧图片 URL（可选）",
            placeholder="https://example.com/cover.png",
            help="模型会以该图片作为视频首帧进行生成。",
        )
        extra_instructions = st.text_area(
            label="补充说明（可选）",
            placeholder="例如：音乐节奏感强，镜头平滑移动。",
            height=160,
        )

    st.divider()
    st.subheader("调用与结果")

    if st.button("🚀 生成视频", use_container_width=True):
        if not token:
            st.error("请先在侧边栏填写 API Token。")
            st.stop()

        if image_url:
            image_err = validate_image_url(image_url, "首帧图片")
            if image_err:
                st.error(image_err)
                st.stop()

        payload = build_payload(
            model=selected_model,
            text_prompt=text_prompt,
            start_image_url=image_url,
            extra_instructions=extra_instructions,
            stream=stream,
        )

        with st.spinner("正在调用接口，请稍候..."):
            try:
                response = send_request(token=token, payload=payload, stream_mode=stream)
            except requests.exceptions.RequestException as err:
                st.error(f"调用失败：{err}")
                st.stop()

        st.code(json.dumps(payload, ensure_ascii=False, indent=4), language="json")

        if not response.ok:
            st.error(f"接口返回错误：HTTP {response.status_code}")
            st.write(response.text)
            st.stop()

        if stream:
            st.success("已建立流式连接，正在接收数据……")
            log_placeholder = st.empty()
            text_buffer: List[str] = []
            raw_lines: List[str] = []

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                if raw_line.startswith("data:"):
                    raw_line = raw_line.split("data:", 1)[1].strip()

                if raw_line == "[DONE]":
                    break

                raw_lines.append(raw_line)
                log_placeholder.code(
                    "\n".join(raw_lines[-40:]) or "(空)",
                    language="json",
                )

                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                content_piece = delta.get("content")
                if content_piece:
                    text_buffer.append(normalize_stream_text(content_piece))

            final_text = "".join(text_buffer).strip()
            if final_text:
                st.markdown(final_text)
                video_url = None
                candidate_url = extract_first_url(final_text)
                if candidate_url and candidate_url.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                    video_url = candidate_url

                if video_url:
                    st.video(video_url)
                    st.markdown(
                        f"下载链接：[{video_url}]({video_url})",
                        help="如果播放器无法直接播放，可复制链接在新标签页打开。",
                    )
                elif candidate_url:
                    st.warning(
                        "检测到的链接可能不是视频文件直链，请手动检查："
                        f" [`{candidate_url}`]({candidate_url})"
                    )
                else:
                    st.info("流式响应中未发现视频下载链接。")
            else:
                st.info("流式响应完成，但未返回文本内容。")
        else:
            try:
                data = response.json()
            except json.JSONDecodeError:
                st.error("接口返回不是有效的 JSON，请检查响应。")
                st.write(response.text)
                st.stop()

            st.success("调用成功！")
            st.json(data)

            video_url = None
            if isinstance(data, dict):
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    contents = message.get("content", [])
                    if contents:
                        first_item = contents[0]
                        if isinstance(first_item, dict):
                            video_url = first_item.get("url") or first_item.get("text")
                        elif isinstance(first_item, str):
                            video_url = first_item

            if video_url and video_url.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                st.video(video_url)
                st.markdown(
                    f"下载链接：[{video_url}]({video_url})",
                    help="如果播放器无法直接播放，可复制链接在新标签页打开。",
                )
            elif video_url:
                st.warning(
                    "接口返回的链接不是识别到的视频直链，已原样展示："
                    f" [`{video_url}`]({video_url})"
                )


if __name__ == "__main__":
    main()

