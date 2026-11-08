"""Opt-in instrumentation of original Python adapter lines, in child only.

The tracer terminates after a declared target first appears. It neither replaces
the adapter implementation nor changes its byte writes. No user session imports
this module unless the isolated test process explicitly supplies PYTHONPATH.
"""
import os,sys
if os.environ.get('RECEIPTCOORDINATOR_INTERIOR_TARGET'):
    target=os.environ['RECEIPTCOORDINATOR_INTERIOR_TARGET']
    script=os.environ['RECEIPTCOORDINATOR_INTERIOR_SCRIPT']
    marker=os.environ['RECEIPTCOORDINATOR_INTERIOR_MARKER']
    def trace(frame,event,arg):
        if event=='line' and frame.f_code.co_filename.endswith(script) and os.path.isfile(target):
            with open(marker,'w',encoding='utf-8') as stream:
                stream.write(str(frame.f_lineno))
            os._exit(87)
        return trace
    sys.settrace(trace)
