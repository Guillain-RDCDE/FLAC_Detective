"""The command-line front end, one concern per module.

``flac_detective.main`` is the entry point and keeps every name it has always
exported; the work is done here:

- ``console``: Rich (when installed), the banner, the per-file console line.
- ``logsetup``: the console-log file and the logging handlers.
- ``workdir``: where progress.json, the report and the log go.
- ``args``: argument parsing and the interactive prompt.
- ``discovery``: turning the user's paths into files to analyse and files to reject.
- ``pool``: the worker pool, its fallback, and the progress-event channel.
- ``output``: the report files and the end-of-run summary.
"""
