#! /usr/bin/env python3

from werkzeug.wrappers import Request, Response
import os


@Request.application
def application(request):
    return Response("Serving...")


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    run_simple("localhost", int(os.environ["PORT"]), application)
