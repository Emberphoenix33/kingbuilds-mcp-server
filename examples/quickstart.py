from mcp_server.app import create_server
from mcp_server.config import Settings

if __name__ == "__main__":
    settings = Settings()
    mcp = create_server(settings)
    mcp.run()