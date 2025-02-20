# Xnat Tools

Tools for Xnat batch processing.


## Installation

Building the package requires Python 3.8 or higher and [setuptools](https://pypi.org/project/setuptools/).
To build and install the package, run:
```shell
python -m pip install .
```


## Commandline usage


### Configuration file

The command line tools require a [JSON](https://en.wikipedia.org/wiki/JSON) configuration file.
Hint: Use `xnat-metadata` to compile an overview of the available tags and values for the mapping and exclusions.

* *URL* (required): The XNAT server URL, for example `"https://central.xnat.org"`.
* *project* (required): The container's Project ID.
* *command* (required for batch processing): A command to execute, defined by a list of arguments. The temporary download directory and subject label are appended to the command. For example, `["myscript.sh", "-v"]`, could be executed as `myscript.sh -v /tmp/1234 subj001`.
* *workers* (optional): The number of parallel workers (default: 1). Subjects are distributed over workers.
* *subjects* (optional): A list of subjects to process. If omitted, all subjects in the container will be processed.
* *mapping* (optional): A dictionary with mapping rules. For example, use `{"T1-image": {"series_description": ".*T1.*"}, "T2-image": {"series_description": ".*T2.*"}}`, to download series with a Series Description containing T1 or T2 into a subdirectory called T1-image or T2-image. Series that do not match a mapping are not downloaded.     
* *exclusions* (optional): A list of exclusion rules. For example: `[{"modality": "CT"}, {"modality": "US"}]` excludes CT and ultrasound series.

Full example:
```json
{
  "url": "https://central.xnat.org",
  "project": "HumanCT",
  "command": ["cmd", "/c", "dir"],
  "workers": 1,
  "subjects": [
    "VHFCT1mm-Ankle",
    "VHFCT1mm-Head"
  ],
  "mapping": {
    "resampled": {"series_description": ".*1mm.*"}
  },
  "exclusions": [
    {"modality": "MR"}
  ]
}
```


### xnat-metadata

This commandline tool writes a [JSON](https://en.wikipedia.org/wiki/JSON) file containing all values for each metadata attribute found in the scans in an XNAT container.
If a mapping is given, then the results are sorted per mapping.
The `xnat-metadata` command requires a configuration file with at least an XNAT URL and project name, and optionally a mapping and exclusions. 

Usage: `xnat-metadata CONFIG_FILE OUTPUT_FILE`


### xnat-batch

This commandline executes a command for each subject in the given list of subjects or for all subjects in the container.
The scans matching to the mappings are downloaded to a temporary directory, sorted per mapping. If no mapping is given, then all scans are downloaded.
The temporary download directory and subject label are appended to the command. For example, `["myscript.sh", "-v"]`, could be executed as `myscript.sh -v /tmp/1234 subj001`.
The `xnat-batch` command requires a configuration file with at least an XNAT URL, project name, and command, and optionally a mapping and exclusions. 

Usage: `xnat-batch CONFIG_FILE`
