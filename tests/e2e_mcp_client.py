import asyncio
import os
import sys

# Đảm bảo có thể import mcp.client
try:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
except ImportError:
    print("Error: Vui lòng cài đặt MCP SDK: pip install mcp")
    sys.exit(1)


async def run_e2e():
    print("🚀 Bắt đầu giả lập MCP Client E2E Test...")
    
    # Thiết lập server parameters để gọi server qua stdio
    # Chú ý: Cần truyền biến môi trường hiện tại để server nhận được KIOKU_ANTHROPIC_API_KEY
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "kioku.server"],
        env=os.environ.copy()
    )

    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Bắt buộc gọi initialize đầu tiên để handshake với Server
                await session.initialize()
                print("✅ Handshake thành công với Kioku MCP Server!")

                # 1. Liệt kê Tools
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print(f"✅ Tìm thấy {len(tool_names)} Tools: {', '.join(tool_names)}")

                # 2. Test Tool: save_memory
                print("\n[TEST] Tool: save_memory")
                save_args = {
                    "text": "Cuối tuần đi cà phê với Mai, thảo luận về dự án OpenClaw rất thú vị.",
                    "mood": "excited",
                    "tags": ["weekend", "project", "openclaw"]
                }
                save_res = await session.call_tool("save_memory", save_args)
                print(f"🔹 Result: {save_res.content[0].text if save_res.content else save_res}")

                # 3. Test Tool: search_memories
                print("\n[TEST] Tool: search_memories (Tri-hybrid search)")
                search_res = await session.call_tool("search_memories", {"query": "Dự án OpenClaw", "limit": 2})
                print(f"🔹 Result: {search_res.content[0].text if search_res.content else search_res}")

                # 4. Test Tool: get_timeline
                print("\n[TEST] Tool: get_timeline")
                timeline_res = await session.call_tool("get_timeline", {"limit": 3})
                print(f"🔹 Result: {timeline_res.content[0].text if timeline_res.content else timeline_res}")

                # 5. Test Tool: recall_related (Knowledge Graph)
                print("\n[TEST] Tool: recall_related (Graph Traversal)")
                recall_res = await session.call_tool("recall_related", {"entity": "Mai", "max_hops": 2})
                print(f"🔹 Result: {recall_res.content[0].text if recall_res.content else recall_res}")

                # 6. Liệt kê Resources
                resources_response = await session.list_resources()
                res_uris = [r.uri for r in resources_response.resources]
                print(f"\n✅ Tìm thấy Resource URIs mapping: {', '.join(res_uris)}")

                # 7. Test Resource: kioku://entities/{entity}
                print("\n[TEST] Resource: kioku://entities/Mai")
                entity_res = await session.read_resource("kioku://entities/Mai")
                # Format của Resource format trả về tuỳ thuộc vào SDK, ta in raw
                print(f"🔹 Result: {entity_res.contents[0].text if hasattr(entity_res, 'contents') else entity_res}")

                # 8. Liệt kê Prompts
                prompts_response = await session.list_prompts()
                prompt_names = [p.name for p in prompts_response.prompts]
                print(f"\n✅ Tìm thấy Prompts: {', '.join(prompt_names)}")

                # 9. Test Prompt: analyze_relationships
                print("\n[TEST] Prompt: analyze_relationships")
                prompt_req = await session.get_prompt("analyze_relationships", {"entity_name": "Mai"})
                print("🔹 Prompt Input (Dành cho LLM):")
                print(prompt_req.messages[0].content.text if prompt_req.messages else prompt_req)

                print("\n🎉 Tất cả bài test Client E2E chạy thành công!")
                
    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình chạy E2E Client: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_e2e())
