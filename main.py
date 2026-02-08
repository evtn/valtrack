import asyncio

from uvicorn import Config, Server

from tabtrack.server import app


async def run_server():
    config = Config(app=app, port=8000, host="0.0.0.0")

    server = Server(config)

    await server.serve()


asyncio.run(run_server())
