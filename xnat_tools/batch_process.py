import json
import os
import subprocess
from getpass import getpass
from tempfile import TemporaryDirectory
from typing import List, Optional

import click as click
import xnat

from .utilities import Mapping, Exclusions, get_mapped_scans, download_scan, match_scan


def batch_process(
        url: str,
        project: str,
        command: List[str],
        subjects: Optional[List[str]] = None,
        mapping: Optional[Mapping] = None,
        exclusions: Optional[Exclusions] = None):
    """
    Downloads scans from Xnat and runs a shell command. The root directory to the downloaded scans is provided as an
    argument to the shell command. In case a mapping is used, such as {"T1": {"series_description": ".*T1.*"}}, then the
    mapped scans will be in a subdirectory with the mapping key name ("T1").

    :param url: Xnat server URL
    :param project: Either the project name or XNAT id.
    :param command: The shell command to execute after the scans have been downloaded.
    :param subjects: A list of either DICOM patient names or XNAT subject IDs.
    :param mapping: A dictionary mapping a scan type to a set of rules.
    :param exclusions: A list of rules for excluding scans.
    """
    user = input('Username: ')
    with xnat.connect(url, user=user or None, password=getpass() or None) as session:
        if project not in session.projects:
            raise KeyError('XNAT project does not exist.')
        project_data = session.projects[project]

        subjects = subjects or [*project_data.subjects]
        for subject in subjects:
            if subject not in project_data.subjects:
                raise KeyError('XNAT subject does not exist in this project.')

        exclusions = exclusions or []
        for subject in subjects:
            experiments = project_data.subjects[subject].experiments

            with TemporaryDirectory() as tmpdir:
                if mapping:
                    mapped_scans = get_mapped_scans(experiments, mapping, exclusions=exclusions)
                    for key, scans in mapped_scans.items():
                        for scan in scans:
                            scan_path = os.path.join(tmpdir, key, scan.id)
                            download_scan(scan, scan_path)
                else:
                    for experiment_id in experiments:
                        experiment_data = experiments[experiment_id]
                        for scan_id in experiment_data.scans:
                            scan = experiment_data.scans[scan_id]
                            if any(match_scan(scan, rule) for rule in exclusions):
                                # This scan should be excluded.
                                continue

                            scan_path = os.path.join(tmpdir, experiment_id, scan_id)
                            download_scan(scan, scan_path)

                subprocess.run(command + [tmpdir], shell=True)


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
        subjects=data.get('subjects'),
        mapping=data.get('mapping'),
        exclusions=data.get('exclusions'),
    )


if __name__ == '__main__':
    batch_process_from_config()
