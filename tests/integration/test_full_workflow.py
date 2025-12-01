"""
测试完整工作流程
需要先启动 API 服务器：uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000
"""

import pytest
import httpx
import asyncio
import time


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_simple(api_base_url, sample_text_file):
    """测试完整工作流程（简单文本，禁用 LLM）"""
    
    async with httpx.AsyncClient(base_url=api_base_url, timeout=120.0) as client:
        # 1. 上传文件
        print("\n📤 步骤 1: 上传文件...")
        with open(sample_text_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )
        
        assert response.status_code == 200, f"上传失败: {response.text}"
        task_id = response.json()["task_id"]
        print(f"✓ 上传成功，task_id: {task_id}")
        
        # 2. 解析文本
        print("\n📝 步骤 2: 解析文本...")
        response = await client.post(
            "/parse",
            json={"task_id": task_id}
        )
        
        assert response.status_code == 200, f"解析失败: {response.text}"
        assert response.json()["status"] == "parsed"
        print(f"✓ 解析成功")
        
        # 3. 生成音频（禁用 LLM 加快测试速度）
        print("\n🎵 步骤 3: 生成音频...")
        response = await client.post(
            "/generate",
            json={
                "task_id": task_id,
                "enable_llm": False  # 禁用 LLM 加快测试
            }
        )
        
        assert response.status_code == 200, f"生成失败: {response.text}"
        assert response.json()["status"] == "generating"
        print(f"✓ 生成任务已启动")
        
        # 4. 轮询查询任务状态（最多等待 60 秒）
        print("\n⏳ 步骤 4: 等待生成完成...")
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = await client.get(f"/task/{task_id}/status")
            assert response.status_code == 200, f"查询状态失败: {response.text}"
            
            status_data = response.json()
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            
            print(f"  状态: {status}, 进度: {progress}%")
            
            if status == "completed":
                print(f"✓ 生成完成！")
                assert "total_chapters" in status_data or "chapters" in status_data
                break
            elif status == "failed":
                error_msg = status_data.get("error", "未知错误")
                pytest.fail(f"任务失败: {error_msg}")
            
            await asyncio.sleep(2)  # 每 2 秒查询一次
        else:
            pytest.fail(f"任务超时（超过 {max_wait} 秒）")
        
        print("\n✅ 完整流程测试通过！")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_multi_chapter(api_base_url, sample_multi_chapter_file):
    """测试完整工作流程（多章节文本）"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=180.0) as client:
        # 1. 上传文件
        print("\n📤 步骤 1: 上传多章节文件...")
        with open(sample_multi_chapter_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample_multi_chapter.txt", f, "text/plain")}
            )

        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"✓ 上传成功，task_id: {task_id}")

        # 2. 解析文本
        print("\n📝 步骤 2: 解析章节...")
        response = await client.post(
            "/parse",
            json={"task_id": task_id}
        )

        assert response.status_code == 200
        parse_data = response.json()
        print(f"✓ 解析成功，消息: {parse_data.get('message', '')}")

        # 3. 生成音频
        print("\n🎵 步骤 3: 生成多章节音频...")
        response = await client.post(
            "/generate",
            json={
                "task_id": task_id,
                "enable_llm": False
            }
        )

        assert response.status_code == 200
        print(f"✓ 生成任务已启动")

        # 4. 轮询状态
        print("\n⏳ 步骤 4: 等待生成完成...")
        max_wait = 120
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = await client.get(f"/task/{task_id}/status")
            assert response.status_code == 200

            status_data = response.json()
            status = status_data.get("status", "unknown")

            print(f"  状态: {status}")

            if status == "completed":
                print(f"✓ 多章节生成完成！")
                break
            elif status == "failed":
                pytest.fail(f"任务失败: {status_data.get('error')}")

            await asyncio.sleep(3)
        else:
            pytest.fail(f"任务超时（超过 {max_wait} 秒）")

        print("\n✅ 多章节流程测试通过！")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_language_interface(api_base_url, sample_text_file):
    """测试多语言界面"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # 测试英语界面
        print("\n🌐 测试英语界面...")
        response = await client.post(
            "/upload",
            params={
                "path": str(sample_text_file),
                "language": "en_US"
            }
        )
        assert response.status_code == 200
        print("✓ 英语界面正常")

        # 测试中文界面
        print("\n🌐 测试中文界面...")
        response = await client.post(
            "/upload",
            params={
                "path": str(sample_text_file),
                "language": "zh_CN"
            }
        )
        assert response.status_code == 200
        print("✓ 中文界面正常")

        print("\n✅ 多语言测试通过！")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(api_base_url):
    """测试错误处理"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # 测试不存在的文件
        print("\n❌ 测试不存在的文件...")
        response = await client.post(
            "/upload",
            params={"path": "/nonexistent/file.txt"}
        )
        assert response.status_code == 404
        print("✓ 正确返回 404")

        # 测试不存在的任务
        print("\n❌ 测试不存在的任务...")
        response = await client.post(
            "/parse",
            json={"task_id": "nonexistent_task"}
        )
        assert response.status_code == 404
        print("✓ 正确返回 404")

        # 测试缺少参数
        print("\n❌ 测试缺少参数...")
        response = await client.post("/upload")
        assert response.status_code == 400
        print("✓ 正确返回 400")

        print("\n✅ 错误处理测试通过！")

