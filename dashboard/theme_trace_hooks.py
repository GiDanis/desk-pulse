"""Private, stdlib hooks shared by the resolver and Qt theme service.

The wrapper guard precedes scopes and metadata construction. The Qt bridge owns
operation outcomes; the resolver knows only the optional primitive recorder.
"""
from functools import wraps


def recorder_for(trace):
    if trace is None:
        return None
    recorder = getattr(trace, 'recorder', trace)
    return recorder if recorder.enabled else None


def trace_enabled(trace):
    return recorder_for(trace) is not None


def trace_span(event):
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            recorder = recorder_for(getattr(self, '_trace', None))
            if recorder is None:
                return function(self, *args, **kwargs)
            with recorder.span(event):
                return function(self, *args, **kwargs)
        return wrapped
    return decorate


def trace_operation(name):
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            trace = getattr(self, '_trace', None)
            recorder = recorder_for(trace)
            if recorder is None:
                return function(self, *args, **kwargs)
            parent_request = recorder.current_request
            with trace.operation(name) as request:
                with recorder.scope(request):
                    try:
                        result = function(self, *args, **kwargs)
                    except BaseException:
                        trace.finished(request, 'failed')
                        raise
                    if result is False:
                        if parent_request is not None and request == parent_request:
                            recorder.record('operation.rejected',request_id=request,operation=name,nested=True)
                        else:
                            trace.finished(request, 'rejected')
                    return result
        return wrapped
    return decorate


def trace_generation(function):
    @wraps(function)
    def wrapped(self, generation, *args, **kwargs):
        trace = getattr(self, '_trace', None)
        if recorder_for(trace) is None:
            return function(self, generation, *args, **kwargs)
        with trace.correlate_generation(generation):
            return function(self, generation, *args, **kwargs)
    return wrapped
