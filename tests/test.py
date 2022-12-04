import sys
sys.path.append(".")
from src import rlim
import asyncio

@rlim.RateLimiter(rlim.Rate(5), rlim.Limit(5, 2))
def stest(i):
    print(i)

@rlim.RateLimiter(rlim.Rate(5), rlim.Limit(5, 2))
async def atest(i):
    print(i)

def main():
    for i in range(100, 120):
        stest(i)
        
    if sys.version_info.minor >= 10:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    tasks = []
    for i in range(200, 220):
        tasks.append(loop.create_task(atest(i)))
    loop.run_until_complete(asyncio.wait(tasks))

if __name__ == "__main__":
    main()
