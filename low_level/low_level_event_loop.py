import uuid
import random


def inner_coroutine(uid):
    for i in range(3):
        print(f"Subroutine of {uid} is called {i} times")
        yield i


def some_coroutine():
    uid = uuid.uuid4()
    for i in range(random.randint(1, 10)):
        print(f'Coroutine number {uid}; iteration {i}')
        yield i
        yield from inner_coroutine(uid)


def event_loop(coroutines):
    generators = [c() for c in coroutines]

    while generators != []:
        for gen in generators:
            try:
                next(gen)
            except StopIteration:
                generators.remove(gen)
                continue


if __name__ == '__main__':
    coroutines = [some_coroutine for _ in range(10)]
    event_loop(coroutines)
