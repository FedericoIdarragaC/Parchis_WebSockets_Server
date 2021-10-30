import asyncio
from src.server.server import Server
import os

if __name__ == "__main__":
    server = Server(os.environ["PORT"])
    