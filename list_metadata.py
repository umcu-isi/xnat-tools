import json
from getpass import getpass
from typing import Optional, List

import click
import xnat

from utilities import Mapping, Exclusions, get_mapped_scans, match_scan


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def list_metadata(
        url: str,
        project: str,
        subjects: Optional[List[str]] = None,
        mapping: Optional[Mapping] = None,
        exclusions: Optional[Exclusions] = None):
    """

    :param url:
    :param project: Can be either the project name or XNAT id.
    :param subjects: Can be either the DICOM patient name or XNAT subject id.
    :param mapping:
    :param exclusions:
    :return:
    """
    results = {key: {} for key in mapping.keys()} if mapping else {}
    user = input('Username: ')
    with xnat.connect(url, user=user, password=getpass()) as session:
        if project not in session.projects:
            raise KeyError('XNAT project does not exist.')
        project_data = session.projects[project]

        subjects = subjects or [*project_data.subjects]
        for subject in subjects:
            if subject not in project_data.subjects:
                raise KeyError('XNAT subject does not exist in this project.')

        exclusions = exclusions or []
        for i, subject in enumerate(subjects, 1):
            experiments = project_data.subjects[subject].experiments
            print(f'Adding data for subject {project_data.subjects[subject].label} ({i}/{len(subjects)})')

            if mapping:
                mapped_scans = get_mapped_scans(experiments, mapping, exclusions=exclusions, allow_incomplete=True)
                for key, scans in mapped_scans.items():
                    for scan in scans:
                        for attribute, value in scan.data.items():
                            if attribute not in results[key]:
                                results[key][attribute] = set()
                            results[key][attribute].add(value)

            else:
                for experiment_id in experiments:
                    experiment_data = experiments[experiment_id]
                    for scan_id in experiment_data.scans:
                        scan = experiment_data.scans[scan_id]
                        if any(match_scan(scan, rule) for rule in exclusions):
                            # This scan should be excluded.
                            continue

                        for attribute, value in scan.data.items():
                            if attribute not in results:
                                results[attribute] = set()
                            results[attribute].add(value)

    return results


@click.command()
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_file", type=click.Path())
def list_metadata_from_config(config_file: str, output_file: str):
    with open(config_file, 'r') as file:
        data = json.load(file)
    results = list_metadata(
        data['url'],
        data['project'],
        subjects=data.get('subjects'),
        mapping=data.get('mapping'),
        exclusions=data.get('exclusions'),
    )
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(results, file, cls=SetEncoder, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    list_metadata_from_config()
