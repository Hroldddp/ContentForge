import time


class Progress:
    def __init__(self, total_steps):
        self.start = time.time()
        self.total_steps = total_steps
        print(f"  Started at: {time.strftime('%H:%M:%S')}")

    def elapsed(self):
        return time.time() - self.start

    def step(self, current, label, estimate=None):
        e = self.elapsed()
        line = f"  [{current}/{self.total_steps}] {label}  ({_fmt(e)} elapsed)"
        print(line)
        if estimate is not None:
            print(f"  ~{_fmt(estimate)} remaining")

    def done(self):
        t = time.time() - self.start
        print(f"  Finished at: {time.strftime('%H:%M:%S')}")
        print(f"  Total time:  {_fmt(t)}")


def _fmt(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"
    # TODO: could use a nicer formatting library for this
    # but writing 5 lines is faster than adding a dependency
