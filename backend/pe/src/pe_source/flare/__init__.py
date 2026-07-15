"""Flare data collection scans."""

__all__ = ["run_flare_events"]


def __getattr__(name):
    if name == "run_flare_events":
        # Third-Party Libraries
        from pe_source.flare.flare_events_script import run_flare_events

        return run_flare_events
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
