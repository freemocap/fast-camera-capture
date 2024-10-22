import asyncio
import time


def wait_1s():
    time.sleep(1.0)


def wait_100ms():
    time.sleep(0.1)


def wait_10ms():
    time.sleep(1e-2)


def wait_1ms():
    time.sleep(1e-3)



async def async_wait_1_sec():
    await asyncio.sleep(1.0)


async def async_wait_10ms():
    await asyncio.sleep(1e-2)


async def async_wait_1ms():
    await asyncio.sleep(1e-3)



if __name__ == "__main__":
    print("Testing wait functions")

    tic = time.perf_counter_ns()
    for i in range(1000):
        wait_1ms()
    toc = time.perf_counter_ns()
    print(f"WAITED 1ms {1000} times in {(toc - tic)/1e9} s")

    tic = time.perf_counter_ns()
    for i in range(1000):
        wait_10ms()
    toc = time.perf_counter_ns()
    print(f"WAITED 10ms {1000} times in {(toc - tic)/1e9} s")


