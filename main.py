from bot import Bot
from cockpit import start_in_thread

if __name__ == "__main__":
    start_in_thread()
    Bot().run()
