import asyncio
import collections
import datetime
import heapq
import threading
import time
from asyncio import events


class EventSimulator(asyncio.AbstractEventLoop):
    def __init__(self):
        self._running = False
        self._immediate = collections.deque()
        self._scheduled = []
        self._exc = None
        self._time = 0

        self._clock_resolution = time.get_clock_info('monotonic').resolution

    def get_debug(self):
        return False

    def time(self):
        return time.monotonic() + self._time

    def _run_once(self):
        """Функция, которая проходит одну итерацию евентлупа"""
        heapq.heapify(self._scheduled)
        end_time = self.time() + self._clock_resolution
        # Чекнуть отложенные задачи, если время, которое записано
        # в них меньше, чем время настоящее - запустить задачу
        while self._scheduled:
            handle = self._scheduled[0]
            if handle._when >= end_time:
                break
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            self._immediate.append(handle)

        # чекнуть задачи, которые нужно запустить сейчас
        while self._immediate:
            if self._immediate:
                h = self._immediate.popleft()
            if not h._cancelled:
                h._run()
            if self._exc is not None:
                raise self._exc

    def run_forever(self):
        # эта функция будет держать евентлуп активным
        # до тех пор, пока одна из задач не закроет его
        self._running = True
        while True:
            if self._running is False:
                break
            self._run_once()

    def run_until_complete(self, future):
        raise NotImplementedError

    def _timer_handle_cancelled(self, handle):
        pass

    def is_running(self):
        return self._running

    def is_closed(self):
        return not self._running

    def stop(self):
        self._running = False

    def close(self):
        self._running = False

    def shutdown_asyncgens(self):
        pass

    def call_exception_handler(self, context):
        self._exc = context.get('exception', None)

    def call_soon(self, callback, *args, **kwargs):
        # создать задачу, вызывается опосредованно через
        # конструктор Task()
        h = asyncio.Handle(callback, args, self)
        self._immediate.append(h)
        return h

    def call_later(self, delay, callback, *args, context=None):
        # отложить задачу на определённое время
        timer = self.call_at(self.time() + delay, callback, *args,
                             context=context)
        if timer._source_traceback:
            del timer._source_traceback[-1]
        return timer

    def call_at(self, when, callback, *args, context=None):
        timer = events.TimerHandle(when, callback, args, self, context)
        if timer._source_traceback:
            del timer._source_traceback[-1]
        heapq.heappush(self._scheduled, timer)
        timer._scheduled = True
        return timer

    def create_task(self, coro):
        # создать таску, таска попадает в очередь
        # через конструктор Task, который вызывает
        # call_soon евентлупа
        async def wrapper():
            try:
                await coro
            except Exception as e:
                self._exc = e
        return asyncio.Task(wrapper(), loop=self)

    def create_future(self):
        return asyncio.Future(loop=self)


class EventSimulatorPolicy(asyncio.AbstractEventLoopPolicy):
    class _Local(threading.local):
        _loop = None
        _set_called = False

    def __init__(self):
        self._local = self._Local()

    def get_event_loop(self):
        """Получает евентлуп из контекста потока"""
        if (self._local._loop is None and
                not self._local._set_called and
                threading.current_thread() is threading.main_thread()):
            self.set_event_loop(self.new_event_loop())

        if self._local._loop is None:
            raise RuntimeError('There is no current event loop')

        return self._local._loop

    def new_event_loop(self):
        self.event_loop = EventSimulator()
        return self.event_loop

    def set_event_loop(self, loop):
        self._local._set_called = True
        assert loop is None or isinstance(loop, asyncio.AbstractEventLoop)
        self._local._loop = loop


async def coro_to_wait():
    for _ in range(10):
        print(f'Current time is {datetime.datetime.now().time()}')
        await asyncio.sleep(1)


async def immediate_coroutine():
    print("Im an immediate coroutine")


async def coro():
    print("Called coro()")
    await coro_to_wait()


policy = EventSimulatorPolicy()
asyncio.set_event_loop_policy(policy)

loop = asyncio.get_event_loop()
asyncio.set_event_loop(loop)
# небольшой хак, чтобы events думал, что евентлуп назначен
asyncio.events._set_running_loop(loop)

loop.create_task(coro())
loop.create_task(immediate_coroutine())
loop.run_forever()
