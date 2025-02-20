import json
from getpass import getpass
from typing import Optional, List, Dict

import click
import xnat

from .utilities import Mapping, Exclusions, get_mapped_scans, match_scan


class SetEncoder(json.JSONEncoder):
    """
    A JSON encoder that encodes sets to JSON lists.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def write_metadata(metadata: Dict, filename: str):
    """
    Writes a dictionary to a JSON file.

    :param metadata: A dictionary.
    :param filename: A filename for the JSON file.
    """
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(metadata, file, cls=SetEncoder, indent=2, ensure_ascii=False)


def get_metadata(
        url: str,
        project: str,
        subjects: Optional[List[str]] = None,
        mapping: Optional[Mapping] = None,
        exclusions: Optional[Exclusions] = None) -> Dict:
    """
    Returns a dictionary containing all values for each metadata attribute found in all scans. If a mapping is given,
    then the results are sorted per mapping.

    :param url: Xnat server URL
    :param project: Either the project name or XNAT id.
    :param subjects: A list of either DICOM patient names or XNAT subject IDs.
    :param mapping: A dictionary mapping a scan type to a set of rules.
    :param exclusions: A list of rules for excluding scans.
    :return: A dictionary containing all values for each metadata attribute.
    """
    results = {key: {} for key in mapping.keys()} if mapping else {}
    user = input('Username: ')
    with xnat.connect(url, user=user or None, password=getpass() or None) as session:
        if project not in session.projects:
            raise KeyError('XNAT project does not exist.')
        project_data = session.projects[project]

        subjects = subjects or list(project_data.subjects.keys())
        for subject in subjects:
            if subject not in project_data.subjects:
                raise KeyError('XNAT subject does not exist in this project:', subject)

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
                for session_data in experiments:
                    for scan in session_data.scans:
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
def get_metadata_from_config(config_file: str, output_file: str):
    """
    Writes a JSON file containing all values for each metadata attribute found in all scans. If a mapping is given,
    then the results are sorted per mapping.
    """
    with open(config_file, 'r') as file:
        data = json.load(file)
    results = get_metadata(
        data['url'],
        data['project'],
        subjects=data.get('subjects'),
        mapping=data.get('mapping'),
        exclusions=data.get('exclusions'),
    )
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(results, file, cls=SetEncoder, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    get_metadata_from_config()
