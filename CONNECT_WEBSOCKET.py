import json

import rel
import websocket

from CONFIG import REDIS_DB, RPC_WEBSOCKET

SUBSCRIBE_MSG = '{"jsonrpc": "2.0", "method": "subscribe", "params": ["tm.event=\'NewBlock\'"], "id": 1}'

# logger
import logging

logger = logging.getLogger(__name__)


# on a new block message, we will clear redis of any values which the config set to -2
# Use this for an indexer in the future?? :D
def on_message(ws, message):

    msg = json.loads(message)

    if msg.get("result") == {}:
        logger.info("Subscribed to New Block with TendermintRPC...")
        return

    # block_height = msg["result"]["data"]["value"]["block"]["header"]["height"]
    block_height = (
        msg.get("result", {})
        .get("data", {})
        .get("value", {})
        .get("block", {})
        .get("header", {})
        .get("height", -1)
    )

    if block_height == -1:
        logger.error("Error: block height not found")
        return

    logger.debug(f"""New Block: {block_height}""")

    # resets all blockOnly keys (balances for example)
    del_keys = REDIS_DB.keys("*;IsBlockOnly;*")
    if len(del_keys) > 0:
        logger.debug(f"Deleting {len(del_keys)} keys...")
        REDIS_DB.delete(*del_keys)


def on_error(ws, error):
    logger.error(error)


def on_close(ws, close_status_code, close_msg):
    logger.info("Closed connection")


def on_open(ws):
    logger.info("Opened connection")
    ws.send(SUBSCRIBE_MSG)
    logger.info("Sent subscribe request")


class TendermintRPCWebSocket:
    def __init__(
        self,
        enableSignal: bool = False,
        enableTrace: bool = False,
        logLevel: int = logging.DEBUG,
    ):
        self.enableSignal = enableSignal

        websocket.enableTrace(enableTrace)  # toggle to show or hide output
        self.ws = websocket.WebSocketApp(
            f"{RPC_WEBSOCKET}",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        logger.setLevel(logLevel)
        logger.addHandler(logging.StreamHandler())

    def start(self):
        if self.enableSignal:
            self.ws.run_forever(dispatcher=rel, reconnect=5)
            self.signal(2, rel.abort)
            self.dispatch()
        else:
            self.run_forever()

    def signal(self, sig, func):
        rel.signal(sig, func)

    def dispatch(self):
        rel.dispatch()


if __name__ == "__main__":
    # websocket.enableTrace(False)  # toggle to show or hide output
    # ws = websocket.WebSocketApp(
    #     f"{RPC_WEBSOCKET}",
    #     on_open=on_open,
    #     on_message=on_message,
    #     on_error=on_error,
    #     on_close=on_close,
    # )

    # ws.run_forever(
    #     dispatcher=rel, reconnect=5
    # )  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
    # rel.signal(2, rel.abort)  # Keyboard Interrupt
    # rel.dispatch()

    tmrpc = TendermintRPCWebSocket(enableSignal=True)  # so we can ctrl+c
    tmrpc.start()
