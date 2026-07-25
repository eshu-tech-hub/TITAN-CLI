# TITAN Windows Service Wrapper
# Install: python windows\titan_service.py install
# Start:   python windows\titan_service.py start
# Stop:    python windows\titan_service.py stop
# Remove:  python windows\titan_service.py remove

import os
import sys
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager


class TitanService(win32serviceutil.ServiceFramework):
    """Windows service wrapper for TITAN."""

    _svc_name_ = "TITAN"
    _svc_display_name_ = "TITAN Trading Intelligence"
    _svc_description_ = (
        "Institutional Trading Intelligence System - "
        "Provides automated market analysis and trade execution."
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.main()

    def main(self):
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_dir)

        self.process = subprocess.Popen(
            [sys.executable, "-m", "titan", "status"],
            cwd=project_dir,
        )

        while True:
            result = win32event.WaitForSingleObject(self.stop_event, 5000)
            if result == win32event.WAIT_OBJECT_0:
                break
            if self.process.poll() is not None:
                break

        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TitanService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TitanService)
