"""Simple Example client connecting to 01_simple_server."""
import sys
import asyncio
from aiohttp_data_handler import WebSocketHandlerClient, create_data_handler
from model import user


DATA_HANDLER = {}

client_handler = create_data_handler(DATA_HANDLER)


class DataHandler(WebSocketHandlerClient):
    def __init__(self, url, user_id=None, ssl=True, logger=None):
        super().__init__(url, DATA_HANDLER, ssl=ssl, logger=logger)
        self.user_id = user_id

    async def on_connect(self, ws):
        await ws.send_json({
            'type': 'message',
            'message': 'hello!'})

    @client_handler
    async def message(self, data, ws):
        print(f'Client received: {data}')
        sys.exit(0)

    def login(self):
        pass

    # TODO: send message to specific person


async def async_main():
    url = 'http://localhost:8080/ws'
    dh = DataHandler(url=url)
    await dh.start()


def main():
    asyncio.run(async_main())

if __name__ == '__main__':
    main()
