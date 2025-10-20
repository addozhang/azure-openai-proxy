#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure OpenAI Proxy Streaming Test Script
测试 Azure OpenAI Proxy 的 streaming 模式功能
"""

import os
import json
import requests
import time
from typing import Generator

def test_streaming_chat():
    """测试 streaming 聊天功能"""
    print("🚀 开始测试 Azure OpenAI Proxy Streaming 模式...")

    # API 端点
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/v1/chat/completions"

    # 测试请求数据
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": "请用中文回答：解释一下什么是人工智能？请用流式响应，每生成一个词就返回一次。"
            }
        ],
        "stream": True,
        "max_tokens": 200,
        "temperature": 0.7
    }

    print(f"📡 发送请求到: {endpoint}")
    print(f"📝 请求内容: {request_data['messages'][0]['content']}")

    try:
        # 发送 POST 请求
        response = requests.post(
            endpoint,
            json=request_data,
            headers={"Content-Type": "application/json"},
            stream=True
        )

        if response.status_code != 200:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            return

        print("✅ 连接成功，开始接收流式响应...")
        print("-" * 50)

        # 处理流式响应
        chunk_count = 0
        full_content = ""

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    chunk_count += 1
                    data_str = line[6:]  # 移除 'data: ' 前缀

                    if data_str == '[DONE]':
                        print("\n" + "-" * 50)
                        print("✅ 流式响应完成")
                        break

                    try:
                        chunk_data = json.loads(data_str)
                        if 'choices' in chunk_data and chunk_data['choices']:
                            choice = chunk_data['choices'][0]
                            if 'delta' in choice and 'content' in choice['delta']:
                                content = choice['delta']['content']
                                if content:
                                    full_content += content
                                    print(content, end='', flush=True)

                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON 解析错误: {e}")

        print(f"\n\n📊 统计信息:")
        print(f"   总块数: {chunk_count}")
        print(f"   总字符数: {len(full_content)}")
        print(f"   完整内容: {full_content}")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保 Azure OpenAI Proxy 服务正在运行")
        print("💡 启动服务: python app.py")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

def test_health_check():
    """测试健康检查端点"""
    print("\n🔍 测试健康检查端点...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data}")
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 健康检查错误: {e}")

def test_models_list():
    """测试模型列表端点"""
    print("\n🔍 测试模型列表端点...")
    try:
        response = requests.get("http://localhost:8000/v1/models")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 模型列表: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 模型列表失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ 模型列表错误: {e}")

def main():
    """主函数"""
    print("🎯 Azure OpenAI Proxy Streaming 测试工具")
    print("=" * 50)

    # 先测试基本端点
    test_health_check()
    test_models_list()

    # 测试 streaming 功能
    test_streaming_chat()

    print("\n🎉 测试完成！")

if __name__ == "__main__":
    main()