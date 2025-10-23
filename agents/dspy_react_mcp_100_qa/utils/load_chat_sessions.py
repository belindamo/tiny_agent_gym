from mcp import ClientSession, StdioServerParameters

from mcp.client.stdio import stdio_client

from typing import List, Dict
import asyncio

async def load_chat_sessions_into_server_memory(session: ClientSession, chat_sessions: List[Dict[str, str]]):
    """Load chat logs into the server memory."""
    print(f"Loading {len(chat_sessions)} chat messages into server memory...")

    for idx, chat_session in enumerate(chat_sessions):
        try:
            formatted_chat = ""
            # Each session has a 'messages' field containing the actual messages
            messages = chat_session.get('messages', [])
            for message in messages:
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                formatted_message = f"{role}: {content}"
                formatted_chat += formatted_message + "\n"
            
            result = await session.call_tool("create_entities", {
                "name": f"Chat Session {idx}",
                "episode_body": formatted_chat,
                "source": "message",
                "source_description": f"Chat session {idx} log.",
                "group_id": "agent_session"
            })
            
            print(f"Added chat session {idx} to server memory.")
            
            # Wait so that the episode are processed
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Error loading session {idx}: {str(e)}")
        # Wait so that the episode are processed
        await asyncio.sleep(10)

    # Search nodes to verify data was loaded
    nodes = await session.call_tool("search_nodes", {
        "query": "rack fest",
    })
    print(f"Found {len(nodes)} nodes in memory")
    print(nodes, "NODES")
    
    return
            

async def load_chat_sessions_into_graphiti(session: ClientSession, chat_sessions: List[Dict[str, str]]):
    """Load chat logs into the Graphiti knowledge graph with session isolation."""
    print(f"Loading {len(chat_sessions)} chat messages into Graphiti...")

    for idx, chat_session in enumerate(chat_sessions):
        try:
            formatted_chat = ""
            # Each session has a 'messages' field containing the actual messages
            messages = chat_session.get('messages', [])
            for message in messages:
                role = message.get('role', 'unknown')
                content = message.get('content', '')
                formatted_message = f"{role}: {content}"
                formatted_chat += formatted_message + "\n"
            
            result = await session.call_tool("add_memory", {
                "name": f"Chat Session {idx}",
                "episode_body": formatted_chat,
                "source": "message",
                "source_description": f"Chat session {idx} log.",
                "group_id": "agent_session"
            })
            
        except Exception as e:
            print(f"Error loading session {idx}: {str(e)}")
            
        # Wait so that the episode are processed
        await asyncio.sleep(10)

    graph = await session.call_tool("search_memory_facts", {
        "query": "How many days before the 'Rack Fest' did I participate in the 'Turbocharged Tuesdays' event?",
    })
    print(graph, "GRAPH")
    return
            