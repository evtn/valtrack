import asyncio
from argparse import ArgumentParser

from uvicorn import Config, Server


async def run_server(host: str = "0.0.0.0", port: int = 8000):
    from valtrack.server import app

    config = Config(app=app, port=port, host=host)

    server = Server(config)

    await server.serve()


if __name__ == "__main__":
    argparser = ArgumentParser()
    argparser.add_argument(
        "--port",
        default=8000,
        type=int,
        help="bind port (default: 8000)",
    )
    argparser.add_argument(
        "--host",
        default="0.0.0.0",
        help='bind hostname (default: "0.0.0.0")',
    )

    args = argparser.parse_args()

    asyncio.run(
        run_server(
            host=args.host,
            port=args.port,
        )
    )
