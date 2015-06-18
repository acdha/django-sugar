# encoding: utf-8
from __future__ import print_function

import inspect
import os
import re
import sys
import time
import uuid
import warnings

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

try:
    import simplejson as json
except ImportError:
    import json


class SpeedTracerMiddleware(object):
    """
    Record server-side performance data for Google Chrome's SpeedTracer

    Getting started:

    1. Download and install Speed Tracer:
        http://code.google.com/webtoolkit/speedtracer/get-started.html
    2. Add this middleware to your MIDDLEWARE_CLASSES
    3. Reload your page
    4. Open SpeedTracer and expand the "Server Trace" in the page's detailed
       report which should look something like http://flic.kr/p/8kwEw3

    NOTE: Trace data is store in the Django cache. Yours must be functional.
    """

    #: Traces will be stored in the cache with keys using this prefix:
    CACHE_PREFIX = getattr(settings, "SPEEDTRACER_CACHE_PREFIX", 'speedtracer-%s')

    #: Help debug SpeedTracerMiddleware:
    DEBUG = getattr(settings, 'SPEEDTRACER_DEBUG', False)

    #: Trace into Django code:
    TRACE_DJANGO = getattr(settings, 'SPEEDTRACER_TRACE_DJANGO', False)

    #: Trace data will be retrieved from here:
    TRACE_URL = getattr(settings, "SPEEDTRACER_API_URL", '/__speedtracer__/')

    def __init__(self):
        warnings.warn("speedtracer middleware has moved from django-sugar to django-speedtracer: see http://pypi.python.org/pypi/django-speedtracer/", DeprecationWarning)

        self.traces = []
        self.call_stack = []

        file_filter = getattr(settings, "SPEEDTRACER_FILE_FILTER_RE", None)
        if isinstance(file_filter, basestring):
            file_filter = re.compile(file_filter)
        elif file_filter is None:
            # We'll build a list of installed app modules from INSTALLED_APPS
            app_dirs = set()
            for app in settings.INSTALLED_APPS:
                try:
                    if app.startswith("django.") and not self.TRACE_DJANGO:
                        continue

                    for k, v in sys.modules.items():
                        if k.startswith(app):
                            app_dirs.add(*sys.modules[app].__path__)
                except KeyError:
                    print >>sys.stderr, "Can't get path for app: %s" % app

            app_dir_re = "(%s)" % "|".join(map(re.escape, app_dirs))

            print  >> sys.stderr, "Autogenerated settings.SPEEDTRACER_FILE_FILTER_RE: %s" % app_dir_re

            file_filter = re.compile(app_dir_re)

        self.file_filter = file_filter

    def trace_callback(self, frame, event, arg):
        if not event in ('call', 'return'):
            return

        if not self.file_filter.match(frame.f_code.co_filename):
            return # No trace

        if self.DEBUG:
            print("%s: %s %s[%s]" % (event, frame.f_code.co_name, frame.f_code.co_filename, frame.f_lineno))

        if event == 'call':
            code = frame.f_code

            class_name = module_name = ""

            module = inspect.getmodule(code)
            if module:
                module_name = module.__name__

            try:
                class_name = frame.f_locals['self'].__class__.__name__
            except (KeyError, AttributeError):
                pass

            new_record = {
                'operation':  {
                    'sourceCodeLocation':  {
                        'className'  :  frame.f_code.co_filename,
                        'methodName' :  frame.f_code.co_name,
                        'lineNumber' :  frame.f_lineno,
                    },
                    'type':  'METHOD',
                    'label':  '.'.join(filter(None, (module_name, class_name, frame.f_code.co_name))),
                },
                'children':  [],
                'range': {"start_time": time.time() },
            }

            new_record['id'] = id(new_record)

            self.call_stack.append(new_record)

            return self.trace_callback

        elif event == 'return':
            end_time = time.time()

            if not self.call_stack:
                print >>sys.stderr, "Return without stack?"
                return

            current_frame = self.call_stack.pop()

            current_frame['range'] = self._build_range(current_frame['range']["start_time"], end_time)

            if not self.call_stack:
                self.traces.append(current_frame)
            else:
                self.call_stack[-1]['children'].append(current_frame)

            return

    def process_request(self, request):
        if not request.path.startswith(self.TRACE_URL):
            request._speedtracer_start_time = time.time()
            sys.settrace(self.trace_callback)
            return

        trace_id = self.CACHE_PREFIX % request.path[len(self.TRACE_URL):]

        data = cache.get(trace_id, {})

        return HttpResponse(json.dumps(data), mimetype="application/json; charset=UTF-8")

    def process_response(self, request, response):
        sys.settrace(None)

        try:
            start_time = request._speedtracer_start_time
        except AttributeError:
            return response

        end_time = time.time()

        trace_id = uuid.uuid4()

        data = {
            'trace':  {
                'id':  str(trace_id),
                'application': 'Django SpeedTracer',
                'date':  time.time(),
                'range': self._build_range(start_time, end_time),
                'frameStack':  {
                    'id': 0,
                    'range': self._build_range(start_time, end_time),
                    'operation':  {
                        'type':  'HTTP',
                        'label':  "{0.method} {0.path}".format(request)
                    },
                    'children': self.traces,
                }
            }
        }

        cache.set(self.CACHE_PREFIX % trace_id, data, getattr(settings, "SPEEDTRACER_TRACE_TTL", 3600))

        response['X-TraceUrl'] = "%s%s" % (self.TRACE_URL, trace_id)

        return response

    def _build_range(self, start_time, end_time):
        return {
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
        }
