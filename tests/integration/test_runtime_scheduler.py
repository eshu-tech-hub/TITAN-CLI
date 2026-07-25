from titan.runtime.scheduler import PipelineScheduler


def test_scheduler_lifecycle():
    scheduler = PipelineScheduler()
    scheduler.start()
    assert scheduler._active is True
    scheduler.stop()
    assert scheduler._active is False
