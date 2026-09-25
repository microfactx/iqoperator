import sys
sys.path.append('.')
import bot
import config

config.COMPOUND_META_DAILY = 14.0
config.COMPOUND_LOSS_DAILY = 10.0

class MockAPI:
    def __init__(self):
        self.api = self
    def close(self):
        pass

b = bot.Bot()
b.api = MockAPI()

# Scenario 1: Bot restarted during the day. Target was hit (balance = 1140, start = 1000)
b._safe_balance = lambda: 1140.0
b._get_daily_base = lambda cb: 1000.0
b.profit = 0.0  # Reset upon restart

print("Should stop (target hit, restarted):", b.stop())

# Scenario 2: Bot ran across midnight. Target is 14% of 1140 = 159.6.
# Balance is 1140, but profit is 140 from the previous day!
b._safe_balance = lambda: 1140.0
b._get_daily_base = lambda cb: 1140.0
b.profit = 140.0

print("Should NOT stop (new day, target not hit):", b.stop())
