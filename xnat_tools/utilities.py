import os
import re
import zipfile
from typing import List, Dict, Callable, Union

from xnat.core import XNATListing
from xnat.mixin import ImageScanData


RegexRule = Dict[str, str]
FunctionRule = Callable[[ImageScanData], bool]
Mapping = Dict[str, Union[RegexRule, FunctionRule]]
Exclusions = List[Union[RegexRule, FunctionRule]]


def scan_label(scan: ImageScanData) -> str:
    """
    Returns a pretty name for the scan.

    :param scan: An Xnat scan.
    :return: Pretty name.
    """
    if 'series_description' in scan.data:
        return f'{scan.id} ({scan.data["series_description"]})'
    else:
        return scan.id


def match_scan(scan: ImageScanData, rule: Union[RegexRule, FunctionRule]):
    """
    Matches a scan to a rule.

    :param scan: An Xnat scan.
    :param rule: Either a regular expression or a function rule.
    :return: True if the scan matches the given rule and false otherwise.
    """
    if isinstance(rule, Callable):
        return rule(scan)
    else:
        return all(re.match(pattern, scan.get(attr, '')) for attr, pattern in rule.items())


def get_mapped_scans(
        experiments: XNATListing,
        mapping: Mapping,
        exclusions: Exclusions,
        allow_incomplete: bool = False) -> Dict[str, List[ImageScanData]]:
    """
    Returns a dictionary that maps a scan type to all scans in the experiments that match the rules for that scan type.

    :param experiments: A list of Xnat experiments.
    :param mapping: A dictionary mapping a scan type to a set of rules.
    :param exclusions: A list of rules for excluding scans.
    :param allow_incomplete: Does not raise an error if none of the scans match to a scan type.
    :return: A dictionary mapping a scan type to a list of Xnat scans.
    """
    mapped_scans = {key: [] for key in mapping.keys()}
    scan_labels = []
    for experiment_id in experiments:
        experiment_data = experiments[experiment_id]
        for scan_id in experiment_data.scans:
            scan = experiment_data.scans[scan_id]
            if any(match_scan(scan, rule) for rule in exclusions):
                # This scan should be excluded.
                continue

            scan_labels.append(scan_label(scan))
            for key, rule in mapping.items():
                if match_scan(scan, rule):
                    mapped_scans[key].append(scan)

    # Warn about not unique matches.
    for key, scans in mapped_scans.items():
        if len(scans) > 1:
            labels = [scan_label(scan) for scan in scans]
            print(f'Multiple matches for {key}: {labels}')

    # Warn about missing scans.
    missing = [key for key, scans in mapped_scans.items() if not scans]
    if any(missing):
        if allow_incomplete:
            print('Mapping incomplete:', f'Missing {missing} in {scan_labels}')
        else:
            raise Exception('Mapping incomplete', f'Missing {missing} in {scan_labels}')

    return mapped_scans


def download_scan(scan: ImageScanData, path: str):
    """
    Downloads a scan to the given path. The path will be created if it does not exist yet.

    :param scan: An Xnat scan.
    :param path: A file path.
    """
    zip_file = path + '.zip'

    print(f'Downloading {scan_label(scan)}: {zip_file}')
    os.makedirs(path, exist_ok=True)
    scan.download(zip_file)

    print(f'Extracting {zip_file} to: {path}')
    with zipfile.ZipFile(zip_file) as zip_ref:
        for zip_info in zip_ref.infolist():
            # Skip directories and extract each file into path.
            if zip_info.filename[-1] != '/':
                zip_info.filename = os.path.basename(zip_info.filename)
                zip_ref.extract(zip_info, path)

    os.remove(zip_file)
