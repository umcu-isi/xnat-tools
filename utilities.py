import os
import re
import zipfile
from typing import List, Dict, Callable, Union

from xnat.core import XNATListing
from xnat.mixin import ImageScanData


RegexRule = Dict[str, str]
FunctionRule = Callable[[ImageScanData], bool]
Mapping = Dict[str, Union[RegexRule, FunctionRule]]
Exclusions = List[RegexRule]


def match_scan(scan: ImageScanData, rule: Union[RegexRule, FunctionRule]):
    if isinstance(rule, Callable):
        return rule(scan)
    else:
        return all(re.match(pattern, scan.get(attr, '')) for attr, pattern in rule.items())


def get_mapped_scans(
        experiments: XNATListing,
        mapping: Mapping,
        exclusions: List[RegexRule]) -> Dict[str, List[ImageScanData]]:
    mapped_scans = {key: [] for key in mapping.keys()}
    series_descriptions = []
    for experiment_id in experiments:
        experiment_data = experiments[experiment_id]
        for scan_id in experiment_data.scans:
            scan = experiment_data.scans[scan_id]
            if any(match_scan(scan, rule) for rule in exclusions):
                # This scan should be excluded.
                print(f'Excluding {scan_id}')
                continue

            series_descriptions.append(scan_id)
            for key, rule in mapping.items():
                if match_scan(scan, rule):
                    if mapped_scans[key]:
                        other_id = mapped_scans[key][0].id
                        print(f'Match for "{key}" not unique: Both {other_id} and {scan_id} match.')
                    else:
                        mapped_scans[key] = scan

    missing = [key for key, scans in mapped_scans if not scans]
    if any(missing):
        raise Exception('Mapping incomplete', f'Missing {missing} in {series_descriptions}')

    return mapped_scans


def download_scan(scan: ImageScanData, path: str):
    zip_file = path + '.zip'

    print(f'Downloading {scan.id}: {zip_file}')
    scan.download(zip_file)

    print(f'Extracting {zip_file} to: {path}')
    os.makedirs(path, exist_ok=True)
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(path)

    os.remove(zip_file)
