"""
Test the complete workflow
Requires the API server to be running first: bash api.sh
"""

import pytest
import httpx
import asyncio
import time


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_simple(api_base_url, sample_text_file):
    """Test the complete workflow (simple text, LLM disabled)"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=120.0) as client:
        # 1. Upload file
        print("\n📤 步骤 1: 上传文件...")
        with open(sample_text_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample.txt", f, "text/plain")}
            )

        assert response.status_code == 200, f"上传失败: {response.text}"
        task_id = response.json()["task_id"]
        print(f"✓ 上传成功，task_id: {task_id}")

        # 2. Parse text
        print("\n📝 步骤 2: 解析文本...")
        response = await client.post(
            "/parse",
            json={"task_id": task_id}
        )

        assert response.status_code == 200, f"解析失败: {response.text}"
        assert response.json()["status"] == "parsed"
        print("✓ 解析成功")

        # 3. Generate audio (disable LLM to speed up testing)
        print("\n🎵 步骤 3: 生成音频...")
        response = await client.post(
            "/generate",
            json={
                "task_id": task_id,
                "enable_llm": False  # Disable LLM to speed up testing
            }
        )

        assert response.status_code == 200, f"生成失败: {response.text}"
        assert response.json()["status"] == "generating"
        print("✓ 生成任务已启动")

        # 4. Poll task status (wait up to 60 seconds)
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
                print("✓ 生成完成！")
                assert "total_chapters" in status_data or "chapters" in status_data
                break
            elif status == "failed":
                error_msg = status_data.get("error", "未知错误")
                pytest.fail(f"任务失败: {error_msg}")

            await asyncio.sleep(2)  # Poll every 2 seconds
        else:
            pytest.fail(f"任务超时（超过 {max_wait} 秒）")

        print("\n✅ 完整流程测试通过！")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_multi_chapter(api_base_url, sample_multi_chapter_file):
    """Test the complete workflow (multi-chapter text)"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=180.0) as client:
        # 1. Upload file
        print("\n📤 步骤 1: 上传多章节文件...")
        with open(sample_multi_chapter_file, "rb") as f:
            response = await client.post(
                "/upload",
                files={"file": ("sample_multi_chapter.txt", f, "text/plain")}
            )

        assert response.status_code == 200
        task_id = response.json()["task_id"]
        print(f"✓ 上传成功，task_id: {task_id}")

        # 2. Parse text
        print("\n📝 步骤 2: 解析章节...")
        response = await client.post(
            "/parse",
            json={"task_id": task_id}
        )

        assert response.status_code == 200
        parse_data = response.json()
        print(f"✓ 解析成功，消息: {parse_data.get('message', '')}")

        # 3. Generate audio
        print("\n🎵 步骤 3: 生成多章节音频...")
        response = await client.post(
            "/generate",
            json={
                "task_id": task_id,
                "enable_llm": False
            }
        )

        assert response.status_code == 200
        print("✓ 生成任务已启动")

        # 4. Poll status
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
                print("✓ 多章节生成完成！")
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
    """Test the multi-language interface"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # Test the English interface
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

        # Test the Chinese interface
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
    """Test error handling"""

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # Test a non-existent file
        print("\n❌ 测试不存在的文件...")
        response = await client.post(
            "/upload",
            params={"path": "/nonexistent/file.txt"}
        )
        assert response.status_code == 404
        print("✓ 正确返回 404")

        # Test a non-existent task
        print("\n❌ 测试不存在的任务...")
        response = await client.post(
            "/parse",
            json={"task_id": "nonexistent_task"}
        )
        assert response.status_code == 404
        print("✓ 正确返回 404")

        # Test missing parameters
        print("\n❌ 测试缺少参数...")
        response = await client.post("/upload")
        assert response.status_code == 400
        print("✓ 正确返回 400")

        print("\n✅ 错误处理测试通过！")

