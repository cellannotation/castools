#!/usr/bin/env python3

"""
Script Description:
This script processes and integrates information from a JSON file and an AnnData (Annotated Data) file,
creating a new AnnData object that incorporates the metadata. The resulting AnnData object is then saved to a new file.

Key Features:
1. Parses command-line arguments for input JSON file, input AnnData file, and output file.
2. Reads and processes the input JSON file and AnnData file.
3. Updates the AnnData object with information from the JSON annotations and root keys.
4. Writes the modified AnnData object to a specified output file.

Usage:
python script.py --json path/to/json_file.json --anndata path/to/anndata_file.h5ad --output path/to/output_file.h5ad
"""

import argparse
import json
from typing import Optional

import anndata

LABELSET_NAME = "name"

LABELSET = "labelset"

ANNOTATIONS = "annotations"

CELL_IDS = "cell_ids"


def read_json_file(file_path):
    """
    Reads and parses a JSON file into a Python dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The JSON data as a Python dictionary.

    Returns None if the file does not exist or if there is an issue
    parsing the JSON content.

    Example:
        json_data = read_json_file('path/to/your/file.json')
        if json_data is not None:
            # Use the parsed JSON data as a dictionary
            print(json_data)
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
        return None


def read_anndata_file(file_path: str) -> Optional[anndata.AnnData]:
    """Load anndata object from a file.

    Args:
        file_path: The path to the file containing the anndata object.

    Returns:
        The loaded anndata object if successful, else None.
    """
    try:
        anndata_obj = anndata.read_h5ad(file_path, backed="r")
        return anndata_obj
    except Exception as e:
        print(f"An error occurred while loading the file: {e}")
        return None


def is_list_of_strings(var):
    """
    Check if a value is a list of strings.

    Parameters:
        var (list or any): The value to be checked.

    Returns:
        bool: True if the value is a list containing only string elements,
              False otherwise.

    """
    return isinstance(var, list) and all(isinstance(item, str) for item in var)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Input JSON file path")
    parser.add_argument("--anndata", required=True, help="Input AnnData file path")
    parser.add_argument(
        "--output",
        help="Output AnnData file name (default: output.h5ad)",
        default="output.h5ad",
    )

    args = parser.parse_args()
    json_file_path = args.json
    anndata_file_path = args.anndata
    output_file_path = args.output

    if anndata_file_path == output_file_path:
        raise ValueError("--anndata and --output cannot be the same")

    input_json = read_json_file(json_file_path)
    input_anndata = read_anndata_file(anndata_file_path)

    # obs
    annotations = input_json[ANNOTATIONS]

    for ann in annotations:
        cell_ids = ann.get(CELL_IDS, [])

        for k, v in ann.items():
            if k == CELL_IDS:
                continue
            key = f"{ann[LABELSET]}--{k}"
            value = v if not isinstance(v, list) else ", ".join(sorted(v))

            input_anndata.obs[key] = ""

            for index_to_insert in ann[CELL_IDS]:
                input_anndata.obs.at[index_to_insert, key] = value

    # uns
    uns_json = {}
    root_keys = list(input_json.keys())
    root_keys.remove(ANNOTATIONS)
    for key in root_keys:
        value = input_json[key]
        if is_list_of_strings(value):
            uns_json[key] = ", ".join(sorted(value))
        elif isinstance(value, str):
            uns_json[key] = value
        else:
            for labelset in value:
                for k, v in labelset.items():
                    if k == LABELSET_NAME:
                        continue
                    new_key = f"{labelset.get(LABELSET_NAME, '')}--{k}"
                    uns_json.update({new_key: v})

    input_anndata.uns.update(uns_json)
    # Close the AnnData file to prevent blocking
    input_anndata.file.close()
    input_anndata.write(output_file_path)
