"""WebSocket client handling base class and decorator creation."""
import asyncio
import json
import logging

import aiohttp
from aiohttp import WSMsgType


def create_data_handler(handler):
    """Create a new data handler decorator."""

    def data_handler(name_or_func):
        """Simplify adding new handler for different data as decorator.

        just set the 'type' of the data you send to the function name to
        call the handler that processes this data. You can also set a name
        to overwrite the type declaration.

        example usage:
        MY_DATA_HANDLER = {}
        my_data_handler = create_data_handler(MY_DATA_HANDLER)

        @my_data_handler
        async def some_name(self, data):
            print(data)  # received data at least {'type': 'some_name'}
        """
        # 1st case: just the @decorator without any name
        if not isinstance(name_or_func, str):
            handler[name_or_func.__name__] = name_or_func

            def _data_handler(*args, **kwargs):
                return name_or_func(*args, **kwargs)
            return _data_handler

        # 2nd case: the @decorator(name) is given
        def _data_handler(f):
            handler[name_or_func] = f

            def __data_handler(*args, **kwargs):
                return f(*args, **kwargs)
            return __data_handler
        return _data_handler
    return data_handler


class WebSocketHandler:
    """Handle incoming WebSocket connections.

    Based on the given data handler, requires 'command_key' attributes
    set in the data to decide which data handle function gets what data.
    """

    def __init__(self, data_handler: dict, logger=None):
        """Set command_key, data handler and logger."""
        self.logger = logger if logger else logging.getLogger(__name__)
        self._command_key = 'type'
        self._data_handler = data_handler

    async def on_connect(self, ws):
        """Provide hook to handle new websocket connection."""
        pass

    async def on_disconnect(self, data):
        """Provide hook to handle lost websocket connection."""
        return

    async def handle_data(self, data, ws):
        """Handle incoming data."""
        cmd = data.get(self._command_key)
        if cmd not in self._data_handler:
            self.logger.error(
                f'Error: unknown command {cmd}'
                f' on {self.__class__.__name__}')
            return
        self.logger.info(f'handle {cmd}...')
        return await self._data_handler[cmd](self, data, ws)


class WebSocketHandlerClient(WebSocketHandler):
    """Connect to a websocket Server and handle data."""

    def __init__(
            self, url: str, data_handler: dict, logger=None, ssl=True):
        """Set session, url and websocket."""
        super().__init__(data_handler, logger)
        self.ws = None
        self.url = url
        self.ssl = ssl
        self.session = aiohttp.ClientSession()

    async def start(self):
        """Connect and start handling loop."""
        try:
            self.logger.info(f'Connecting to {self.url}...')
            async with self.session.ws_connect(self.url, ssl=self.ssl) as ws:
                self.ws = ws
                await self.on_connect(ws)
                async for message in ws:
                    data = json.loads(message.data)
                    await self.handle_data(data, ws)
        except asyncio.exceptions.CancelledError:
            self.logger.warn('Keyboard Interrupt, exiting...')
        finally:
            # cleanup on error - close all connections
            if self.ws:
                await self.ws.close()
            if self.session:
                await self.session.close()
            await self.on_disconnect(None)


class WebSocketHandlerServer(WebSocketHandler):
    """Handle incoming WebSocket connections.

    Based on the given data handler, requires 'type' attributes
    set in the data to decide which data handle function gets what data.
    """

    def __init__(self, data_handler: dict, logger=None):
        """Set data handler dict and client_id."""
        super().__init__(data_handler, logger)
        self.websockets = []
        self.client_id = 'client_id'
        self._command_key = 'type'

    async def broadcast_json(self, msg):
        """Send data from server to all clients."""
        for ws in self.websockets:
            if not ws.closed:
                await ws.send_json(msg)

    async def handle(self, ws):
        """Handle incoming connection."""
        ws_data = None
        try:
            self.websockets.append(ws)
            await self.on_connect(ws)
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    self.logger.error(
                        'WS connection closed with exception '
                        f'{ws.exception()}')
                elif msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    ret = await self.handle_data(data, ws)
                    if ret:
                        ws_data = ret
        finally:
            self.websockets.remove(ws)
            if not ws.closed:
                await ws.close()
            await self.on_disconnect(ws_data)
