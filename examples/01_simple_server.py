"""Simple Example server using WebSocket Handler."""
from aiohttp import web
from websocket_common import WebSocketHandlerServer, create_data_handler

HANDLER_DICT = {}
handler = create_data_handler(HANDLER_DICT)


class Server(WebSocketHandlerServer):
    def __init__(self, logger=None):
        super().__init__(HANDLER_DICT, logger=logger)
    
    @handler
    async def message(self, data, ws):
        print(f'Server received: {data}')
        # broadcast message back to all clients
        await self.broadcast_json(data)


def main():
    server = Server()
    routes = web.RouteTableDef()
    
    @routes.get('/ws')
    async def ws(request):
        """Store offer when a new sender connects."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await server.handle(ws)
        return ws

    app = web.Application()
    app.add_routes(routes)
    web.run_app(app)


if __name__ == '__main__':
    main()