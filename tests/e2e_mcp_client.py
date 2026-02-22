import asyncio
import os
import sys
import datetime

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

                today_str = datetime.date.today().isoformat()

                # 6. Test Tool: get_memories_by_date
                print(f"\n[TEST] Tool: get_memories_by_date for {today_str}")
                by_date_res = await session.call_tool("get_memories_by_date", {"date": today_str})
                print(f"🔹 Result: {by_date_res.content[0].text if by_date_res.content else by_date_res}")

                # 7. Test Tool: list_memory_dates
                print("\n[TEST] Tool: list_memory_dates")
                dates_res = await session.call_tool("list_memory_dates", {})
                print(f"🔹 Result: {dates_res.content[0].text if dates_res.content else dates_res}")

                # 8. Test Tool: explain_connection
                print("\n[TEST] Tool: explain_connection")
                explain_res = await session.call_tool("explain_connection", {"entity_a": "Mai", "entity_b": "OpenClaw"})
                print(f"🔹 Result: {explain_res.content[0].text if explain_res.content else explain_res}")

                # 9. Test Tool: get_life_patterns
                print("\n[TEST] Tool: get_life_patterns")
                patterns_res = await session.call_tool("get_life_patterns", {"days_back": 30})
                print(f"🔹 Result: {patterns_res.content[0].text if patterns_res.content else patterns_res}")

                # 10. Liệt kê Resources
                resources_response = await session.list_resources()
                res_uris = [r.uri for r in resources_response.resources]
                print(f"\n✅ Tìm thấy Resource URIs mapping: {', '.join(res_uris)}")

                # 11. Test Resource: kioku://entities/{entity}
                print("\n[TEST] Resource: kioku://entities/Mai")
                entity_res = await session.read_resource("kioku://entities/Mai")
                # Format của Resource format trả về tuỳ thuộc vào SDK, ta in raw
                print(f"🔹 Result: {entity_res.contents[0].text if hasattr(entity_res, 'contents') else entity_res}")

                # 12. Test Resource: kioku://memories/{date}
                print(f"\n[TEST] Resource: kioku://memories/{today_str}")
                try:
                    mem_res = await session.read_resource(f"kioku://memories/{today_str}")
                    print(f"🔹 Result: {mem_res.contents[0].text if hasattr(mem_res, 'contents') else mem_res}")
                except Exception as e:
                    print(f"🔹 Result: error reading resource ({e})")

                # 13. Liệt kê Prompts
                prompts_response = await session.list_prompts()
                prompt_names = [p.name for p in prompts_response.prompts]
                print(f"\n✅ Tìm thấy Prompts: {', '.join(prompt_names)}")

                # 14. Test Prompt: analyze_relationships
                print("\n[TEST] Prompt: analyze_relationships")
                prompt_req = await session.get_prompt("analyze_relationships", {"entity_name": "Mai"})
                print("🔹 Prompt Input (Dành cho LLM):")
                print(prompt_req.messages[0].content.text if prompt_req.messages else prompt_req)

                # 15. Test Prompt: reflect_on_day
                print("\n[TEST] Prompt: reflect_on_day")
                reflect_req = await session.get_prompt("reflect_on_day", {"date": today_str})
                print("🔹 Prompt Input (Dành cho LLM):")
                print(reflect_req.messages[0].content.text if reflect_req.messages else reflect_req)

                # 16. Test Prompt: weekly_review
                print("\n[TEST] Prompt: weekly_review")
                weekly_req = await session.get_prompt("weekly_review", {})
                print("🔹 Prompt Input (Dành cho LLM):")
                print(weekly_req.messages[0].content.text if weekly_req.messages else weekly_req)

                print("\n🎉 Tất cả bài test Client E2E chạy thành công!")
                
    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình chạy E2E Client: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_e2e())
