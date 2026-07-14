# PRD: Claude MCP Server Setup (POC)
**Opportunity:** Upwork #2 - Claude MCP Server Setup & Local AI Agent Integration  
**Client:** Fort Wayne IN, established (145 hires, $2.9K spent, 10 active)  
**Budget:** $10 fixed (ongoing project = real opportunity)  
**Score:** 15/20

---

## Scope (POC Only)

Build a **minimal MCP server** that demonstrates the architecture. Not a full production system.

### Deliverables
1. **1 working MCP server** (Python or Node.js)
2. **2 custom tools** (file read + simple data transformation)
3. **Claude Desktop config** showing how to connect
4. **Basic documentation** (setup, usage, extending)

**Out of Scope:**
- Production deployment
- Multiple MCP servers
- Complex workflows
- PDF generation
- Dashboard development

---

## Technical Requirements

### MCP Server Stack
**Option A: Python (Recommended)**
- **Framework:** FastAPI
- **MCP SDK:** `mcp` Python package
- **Transport:** stdio (local Claude Desktop connection)

**Option B: Node.js**
- **Framework:** Express
- **MCP SDK:** `@modelcontextprotocol/sdk`
- **Transport:** stdio

### Custom Tools (POC)

**Tool 1: Read File**
```python
# Input: {"path": "/path/to/file.txt"}
# Output: {"content": "file contents here..."}
# Security: Restrict to specific directory
```

**Tool 2: Simple Data Transform**
```python
# Input: {"data": {...}, "operation": "sum|average|count"}
# Output: {"result": 42}
# Purpose: Demonstrate tool-use pattern
```

### Claude Desktop Config
```json
{
  "mcpServers": {
    "local-tools": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "ALLOWED_DIR": "/home/user/documents"
      }
    }
  }
}
```

---

## Acceptance Criteria

**Must Have:**
- [ ] MCP server runs locally (no external dependencies)
- [ ] Claude Desktop can discover and call the tools
- [ ] File read tool works with basic security (directory restriction)
- [ ] Data transform tool works (sum/average/count)
- [ ] Basic README (how to set up, how to add new tools)
- [ ] **Deployed and running on kingbuilds.dev** (publicly accessible MCP endpoint)
- [ ] **2 custom tools documented** with usage examples
- [ ] **Setup guide** showing how to connect Soliven's architecture as reference implementation
- [ ] **Clean landing page** on kingbuilds.dev explaining what the MCP server does
- [ ] **Live demo functionality** - visitors can see the tools working and how to integrate

**Nice to Have:**
- [ ] Error handling (invalid file paths, bad data)
- [ ] Logging (what tools were called, when)
- [ ] Example prompts showing tool usage
- [ ] Reference to Soliven's architecture in documentation

**Out of Scope:**
- Authentication (local only for demo)
- Multiple MCP servers
- Complex workflows beyond the 2 POC tools
- PDF generation
- Dashboard development

---

## Client Communication

### Phase 1: Discovery Call (30 min)
Ask:
- What's your use case? (What do you want Claude to access/transform?)
- Do you have Claude Desktop installed?
- What's your technical comfort level? (Can you run Python/Node?)
- What's the end goal? (One-time setup vs. ongoing development?)

### Phase 2: Implementation (2-3 hours)
- Set up MCP server skeleton
- Implement 2 custom tools (file read + data transform)
- Configure Claude Desktop connection
- Test tool calls
- Create landing page on kingbuilds.dev with setup guide
- Document reference implementation (Soliven's architecture)

### Phase 2.5: Deployment (30 min)
- Deploy MCP server to kingbuilds.dev
- Deploy landing page with documentation
- Test public accessibility
- Verify Claude Desktop can connect to deployed endpoint

### Phase 3: Handoff (30 min)
- Demo working MCP server
- Show how to add new tools
- Provide setup instructions for their machine

---

## Risk Mitigation

**Risk:** Client can't run the MCP server (environment issues)  
**Mitigation:** Provide step-by-step setup guide + record quick video walkthrough

**Risk:** Client wants more complex tools than POC scope  
**Mitigation:** Show them the pattern, quote additional tools at $50/tool

**Risk:** MCP spec changes (it's still evolving)  
**Mitigation:** Use latest official SDK, document version

---

## Pricing Strategy

**POC Price:** $50 flat (higher than their $10 budget, but signals quality)  
**Alternative:** $10 for setup + $30/hour for additional tools

**Upsell Opportunities:**
- Custom tool development ($50/tool)
- Complex data transformations ($100/workflow)
- Production deployment consulting ($200/session)
- Monthly retainer for MCP server maintenance ($100/month)
- Full Soliven architecture replication ($500-1000)

**KingBuilds.dev Showcase Value:**
- Public demo drives inbound leads
- Proves capability for future clients
- Can reference in proposals: "See working example at kingbuilds.dev"

---

## Success Metrics (Client Perspective)

- MCP server starts in < 30 seconds
- Claude can call tools and get responses
- Client understands how to add new tools
- Clear documentation they can follow

---

## Proposal Angle

> "I build Claude MCP servers that integrate tightly with local workflows. Here's what I'll deliver:
> 
> - Working MCP server (Python or Node.js - your choice)
> - 2 custom tools that solve your immediate needs
> - Claude Desktop configuration (so you can use it today)
> - Documentation on how to extend it
> 
> **Timeline:** 2-3 hours  
> **Price:** $50 flat
> 
> **Why me:** I'm literally doing this right now - I have a Claude MCP server running that handles code execution, file management, and workflow automation. I know the patterns that work.
> 
**What you'll be able to do after:**
- Add custom tools in 15 minutes
- Connect Claude to your local files/data
- Build complex workflows with tool chains
- See a working reference implementation (Soliven architecture)

**Demo available at:** kingbuilds.dev (live MCP server you can connect to)

**Next step:** If you want, I can show you a 5-minute demo of what this looks like in Claude Desktop. Then we'll scope your specific tools.

**Risk reversal:** If you can't get it running, you don't pay."

---

## Next Steps

1. Client accepts proposal
2. Schedule 30-min discovery call (understand their specific tool needs)
3. Build MCP server with their 2 priority tools (2-3 hours)
4. Demo + handoff (30 min)
5. Quote additional tools or monthly retainer if interested

---

## Technical Implementation Notes

### Python MCP Server Skeleton
```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

server = Server("local-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="read_file",
            description="Read a file from allowed directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="transform_data",
            description="Transform numeric data",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "array", "items": {"type": "number"}},
                    "operation": {"type": "string", "enum": ["sum", "average", "count"]}
                },
                "required": ["data", "operation"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "read_file":
        path = arguments["path"]
        # Security check
        if not path.startswith(ALLOWED_DIR):
            return [TextContent(type="text", text=f"Access denied: {path}")]
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "transform_data":
        data = arguments["data"]
        operation = arguments["operation"]
        
        if operation == "sum":
            result = sum(data)
        elif operation == "average":
            result = sum(data) / len(data) if data else 0
        elif operation == "count":
            result = len(data)
        else:
            result = 0
        
        return [TextContent(type="text", text=f"Result: {result}")]

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    
    asyncio.run(main())
```

### Requirements
```txt
mcp>=1.0.0
```

### Run Command
```bash
python mcp_server.py
```
