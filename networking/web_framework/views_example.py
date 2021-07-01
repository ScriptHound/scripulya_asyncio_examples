from networking.web_framework.core import (
    add_route, run_app
)


@add_route(route='/my_another_view')
async def another_view(request):
    return "Hey I'm an another view"


@add_route(route='/favicon.ico')
async def favicon(request):
    return "browser requested this"


@add_route(route='/')
async def root(request):
    return "Some text"


@add_route(route='/index')
async def index(request):
    method = request['method']
    return f"Im an index page sent with method {method}"


run_app('127.0.0.1', 8000)
