import json
import os
import queue
import subprocess
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from tempfile import TemporaryDirectory
from threading import Event
from typing import List, Optional, Dict

import click as click
import xnat

from .utilities import Mapping, Exclusions, get_mapped_scans, download_scan, match_scan


class DownloadJob:
    def __init__(self, subject: str, tmpdir: str):
        self.subject = subject
        self.tmpdir = tmpdir
        self._event = Event()
        self.error: Optional[str] = None
        self.scans: Dict[str, List[str]] = {}

    def finish(self):
        self._event.set()

    def wait(self):
        self._event.wait()


def process_subject(command: List[str], subject: str, label: str, download_queue: queue.Queue):
    with TemporaryDirectory() as tmpdir:
        # Schedule downloads (executed from main thread).
        job = DownloadJob(subject, tmpdir)
        download_queue.put(job)

        # Wait for downloads to finish and execute the command.
        job.wait()
        with open(f"{label}.log", "w") as logfile:
            if job.error:
                logfile.write(f'Error while downloading scans: {job.error}')
            else:
                cmd = command + [tmpdir, label]
                scans = '\n'.join(f'  {key}: {val}' for key, val in job.scans.items())
                logfile.write(f'Downloaded scans:\n{scans}\n\n')
                logfile.write(f'Running command: {" ".join(cmd)}\n\n')
                logfile.flush()
                subprocess.run(cmd, stdout=logfile, stderr=logfile)


def batch_process(
        url: str,
        project: str,
        command: List[str],
        workers: int = 1,
        subjects: Optional[List[str]] = None,
        mapping: Optional[Mapping] = None,
        exclusions: Optional[Exclusions] = None):
    """
    Downloads scans from Xnat and runs a shell command. The root directory to the downloaded scans is provided as an
    argument to the shell command, as well is the subject label. In case a mapping is used, such as
        {"T1": {"series_description": ".*T1.*"}},
    then the mapped scans will be in a subdirectory with the mapping key name ("T1").

    :param url: Xnat server URL
    :param project: Either the project name or XNAT id.
    :param command: The shell command to execute after the scans have been downloaded.
    :param workers: Number of parallel workers executing the command.
    :param subjects: A list of either DICOM patient names or XNAT subject IDs.
    :param mapping: A dictionary mapping a scan type to a set of rules.
    :param exclusions: A list of rules for excluding scans.
    """
    user = input('Username: ')

    executor = ThreadPoolExecutor(max_workers=workers)
    download_queue = queue.Queue()

    with xnat.connect(url, user=user or None, password=getpass() or None) as session:
        if project not in session.projects:
            raise KeyError('XNAT project does not exist.')
        project_data = session.projects[project]

        subjects = subjects or list(project_data.subjects.keys())
        for subject in subjects:
            if subject not in project_data.subjects:
                raise KeyError('XNAT subject does not exist in this project:', subject)

        # Schedule jobs for all subjects.
        exclusions = exclusions or []
        futures = []
        for subject in subjects:
            label = project_data.subjects[subject].label
            futures.append(executor.submit(process_subject, command, subject, label, download_queue))

        # Handle all downloads.
        while any(not f.done() for f in futures):
            try:
                job = download_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                experiments = project_data.subjects[job.subject].experiments
                if mapping:
                    mapped_scans = get_mapped_scans(experiments, mapping, exclusions=exclusions)
                    for key, scans in mapped_scans.items():
                        for scan in scans:
                            scan_path = os.path.join(job.tmpdir, key, scan.id)
                            download_scan(scan, scan_path)
                            job.scans[scan.id] = scan_path
                else:
                    for session_data in experiments:
                        for scan in session_data.scans:
                            if any(match_scan(scan, rule) for rule in exclusions):
                                # This scan should be excluded.
                                continue

                            scan_path = os.path.join(job.tmpdir, session_data.label, scan.id)
                            download_scan(scan, scan_path)
                            job.scans[scan.id] = scan_path
            except Exception as exc:
                job.error = str(exc)
            finally:
                job.finish()

    # Wait until all jobs are finished and shutdown.
    executor.shutdown()


@click.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
def batch_process_from_config(config_file: str):
    """
    Downloads scans from Xnat and runs a shell command.
    """
    with open(config_file, 'r') as file:
        data = json.load(file)
    batch_process(
        data['url'],
        data['project'],
        data['command'],
        workers=data.get('workers', 1),
        subjects=data.get('subjects'),
        mapping=data.get('mapping'),
        exclusions=data.get('exclusions')
    )


if __name__ == '__main__':
    batch_process_from_config()
