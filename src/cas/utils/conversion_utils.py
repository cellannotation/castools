import itertools
from typing import Any, Dict, List, Tuple

import anndata as ad
import pandas as pd

from cas.accession.hash_accession_manager import HashAccessionManager


def calculate_labelset_rank(input_list: List[str]) -> Dict[str, int]:
    """
    Assign ranks to items in a list.

    Args:
        input_list (List[str]): The list of items.

    Returns:
        Dict[str, int]: A dictionary where keys are items from the input list and
        values are their corresponding ranks (0-based).

    """
    list_length = len(input_list)
    return {item: list_length - 1 - rank for rank, item in enumerate(input_list)}
    # return {item: rank for rank, item in enumerate(input_list)}


def calculate_labelset(
    obs: pd.DataFrame, labelsets: List[str]
) -> Dict[str, Dict[str, Any]]:
    """
    Calculates labelset dictionary based on the provided observations.

    Args:
        obs (pd.DataFrame): DataFrame containing observations.
        labelsets (List[str]): List of labelsets.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary where keys are labelsets and values are dictionaries containing:
            - "members": set of members for the labelset.
            - "rank": rank of the labelset.
    """
    labelset_dict = {}
    labelset_rank_dict = calculate_labelset_rank(labelsets)
    for item in labelsets:
        labelset_dict.update(
            {
                item: {
                    "members": set(obs[item]),
                    "rank": str(labelset_rank_dict.get(item)),
                }
            }
        )
    return labelset_dict


def get_cell_ids(
    anndata_obs: pd.DataFrame, labelset: str, cell_label: str
) -> List[str]:
    """
    Get cell IDs from an AnnData dataset based on a specified labelset and cell label.

    Args:
        anndata_obs: The observations DataFrame (`obs`) of an AnnData object containing the dataset. This DataFrame
            should include columns for cell type ontology term IDs and cell types.
        labelset: Labelset to filter.
        cell_label: The value of the cell label used to filter rows in `anndata_obs`.

    Returns:
        List[str]: List of cell IDs.
    """
    cell_label_lower = str(cell_label).lower()
    return anndata_obs.index[
        anndata_obs[labelset].astype(str).str.lower() == cell_label_lower
    ].tolist()


def get_cl_annotations_from_anndata(
    anndata_obs: pd.DataFrame, columns_name: str, cell_label: str
) -> Tuple[str, str]:
    """
    Retrieves cell ontology term ID and cell ontology term for a given cell label from the observation DataFrame
        of an AnnData object.

    Args:
        anndata_obs: The observations DataFrame (`obs`) of an AnnData object containing the dataset. This DataFrame
            should include columns for cell type ontology term IDs and cell types.
        columns_name: The name of the column in `anndata_obs` used for filtering based on the cell label.
        cell_label: The value of the cell label used to filter rows in `anndata_obs`.

    Returns:
        tuple: A tuple containing two elements:
            - The first element is the cell type ontology term ID associated with the given cell label.
            - The second element is the cell type (ontology term) associated with the given cell label.
    """
    filtered_df = anndata_obs[anndata_obs[columns_name] == cell_label]

    cell_ontology_term_id = filtered_df["cell_type_ontology_term_id"].iloc[0]
    cell_ontology_term = filtered_df["cell_type"].iloc[0]

    return cell_ontology_term_id, cell_ontology_term


def generate_parent_cell_lookup(anndata, labelset_dict):
    """
    Generates a lookup dictionary mapping cell labels to various metadata, including cell IDs, rank,
    and cell ontology terms. This function is designed to precompute the lookup information needed for
    CAS annotation generation, especially useful when hierarchy inclusion is desired.

    Args:
        anndata (ad.AnnData): The AnnData object containing the single-cell dataset,
                              including metadata in anndata.obs.
        labelset_dict (Dict[str, Any]): A dictionary where keys are labelset names and values
                                        are dictionaries containing members and their ranks.

    Returns:
        Dict[str, Any]: A dictionary where each key is a cell label and each value is another
                        dictionary containing keys for 'cell_ids' (a set of cell IDs associated
                        with the label), 'rank', 'cell_ontology_term_id', and 'cell_ontology_term'.
    """
    accession_manager = HashAccessionManager()
    parent_cell_look_up = {}
    for k, v in labelset_dict.items():
        for label in v["members"]:
            cell_ontology_term_id, cell_ontology_term = get_cl_annotations_from_anndata(
                anndata.obs, k, label
            )
            cell_ids = get_cell_ids(anndata.obs, k, label)
            cell_set_accession = accession_manager.generate_accession_id(
                cell_ids=cell_ids, labelset=k
            )

            if label in parent_cell_look_up:
                parent_cell_look_up[label]["cell_ids"].update(cell_ids)
            else:
                parent_cell_look_up[label] = {
                    "cell_ids": set(cell_ids),
                    "accession": cell_set_accession,
                    "rank": v.get("rank"),
                    "cell_ontology_term_id": cell_ontology_term_id,
                    "cell_ontology_term": cell_ontology_term,
                }
    return parent_cell_look_up


def generate_cas_annotations(
    anndata: ad.AnnData,
    cas: Dict[str, Any],
    labelset_dict: Dict[str, Any],
    parent_cell_look_up: Dict[str, Any],  # Add this parameter
):
    """
    Generates CAS annotations based on the provided AnnData object and updates the CAS
    dictionary with new annotations. This function can optionally use a precomputed
    parent cell lookup dictionary to enrich the annotations with hierarchical information.

    Args:
        anndata (ad.AnnData): The AnnData object containing the single-cell dataset, including metadata in anndata.obs.
        cas (Dict[str, Any]): The CAS dictionary to be updated with annotations. Expected to have a key
            'annotations' where new annotations will be appended.
        labelset_dict (Dict[str, Any]): A dictionary defining labelsets and their members. This is used to match cell
            labels with their respective metadata and annotations.
        parent_cell_look_up (Dict[str, Any]): A precomputed dictionary containing hierarchical metadata about cell
            labels, which is used to enrich annotations if `include_hierarchy` is True.

    Returns:
        None: The function directly updates the `cas` dictionary with new annotations. The `parent_cell_look_up` is
        used for enrichment and must be generated beforehand if hierarchical information is to be included.
    """
    # accession_manager = HashAccessionManager()

    for k, v in labelset_dict.items():
        for label in v["members"]:
            labelset = k
            cell_ids = get_cell_ids(anndata.obs, k, label)
            # cell_set_accession = accession_manager.generate_accession_id(cell_ids=cell_ids, labelset=labelset)

            rationale = None
            rationale_dois = None
            marker_gene_evidence = None
            synonyms = None
            category_fullname = None
            category_cell_ontology_exists = None
            category_cell_ontology_term_id = None
            category_cell_ontology_term = None

            anno_init = {
                "labelset": labelset,
                "cell_label": label,
                "cell_fullname": label,
                "cell_set_accession": parent_cell_look_up[label]["accession"],
                "cell_ontology_term_id": parent_cell_look_up[label][
                    "cell_ontology_term_id"
                ],
                "cell_ontology_term": parent_cell_look_up[label]["cell_ontology_term"],
                "cell_ids": cell_ids,
                "rationale": rationale,
                "rationale_dois": rationale_dois,
                "marker_gene_evidence": marker_gene_evidence,
                "synonyms": synonyms,
                "category_fullname": category_fullname,
                "category_cell_ontology_exists": category_cell_ontology_exists,
                "category_cell_ontology_term_id": category_cell_ontology_term_id,
                "category_cell_ontology_term": category_cell_ontology_term,
            }
            # Exclude keys with None values
            cas.get("annotations").append(
                {k: v for k, v in anno_init.items() if v is not None}
            )


def update_parent_info(
    value: Dict[str, Any], parent_key: str, parent_value: Dict[str, Any]
):
    """Updates parent information in a child item's dictionary.

    Args:
        value (Dict[str, Any]): The child item's dictionary to be updated.
        parent_key (str): The key of the parent item.
        parent_value (Dict[str, Any]): The parent item's dictionary.

    This function modifies `value` to include `parent` (using `parent_key`),
    `p_accession`, and `parent_rank` based on `parent_value`.
    """
    value.update(
        {
            "parent": parent_key,
            "p_accession": parent_value.get("accession"),
            "parent_rank": parent_value.get("rank"),
        }
    )


def add_parent_cell_hierarchy(parent_cell_look_up: Dict[str, Any]):
    """
    Processes parent cell hierarchy information and updates CAS dictionary annotations accordingly.

    Args:
        parent_cell_look_up (Dict[str, Any]): Dictionary containing parent cell information.

    Returns:
        None
    """
    # Establish parent-child relationships
    for (key, value), (inner_key, inner_value) in itertools.product(
        parent_cell_look_up.items(), repeat=2
    ):
        if (
            key == inner_key
            or value.get("parent")
            and value.get("parent_rank", 0) <= inner_value.get("rank")
        ):
            continue

        if value["cell_ids"] != inner_value["cell_ids"] and value["cell_ids"].issubset(
            inner_value["cell_ids"]
        ):
            update_parent_info(value, inner_key, inner_value)
        elif value["cell_ids"] == inner_value["cell_ids"]:
            if int(inner_value["rank"]) < int(value["rank"]):
                update_parent_info(inner_value, key, value)
            elif int(value["rank"]) < int(inner_value["rank"]):
                update_parent_info(value, inner_key, inner_value)
            else:
                raise ValueError(
                    f"{key} and {inner_key} cell labels have the same cell_ids. Cell_ids can't be "
                    f"identical at the same rank."
                )


def add_parent_hierarchy_to_annotations(
    cas: Dict[str, Any], parent_cell_look_up: Dict[str, Any]
):
    """
    Adds parent hierarchy information to annotations in the CAS dictionary.

    Args:
        cas (Dict[str, Any]): The CAS dictionary containing annotations.
        parent_cell_look_up (Dict[str, Any]): Dictionary containing parent cell information.

    Returns:
        None
    """
    annotation_list = cas.get("annotations", [])
    for annotation in annotation_list:
        parent_info = parent_cell_look_up.get(annotation.get("cell_label"), {})
        parent = parent_info.get("parent")
        p_accession = parent_info.get("p_accession")
        if parent and p_accession:
            # Add parent data to the annotation
            annotation.update(
                {
                    "parent_cell_set_name": parent,
                    "parent_cell_set_accession": p_accession,
                }
            )
            # Remove redundant CL annotations
            parent_dict = parent_cell_look_up.get(parent, {})
            if parent_dict.get("cell_ontology_term_id") == annotation.get(
                "cell_ontology_term_id"
            ) and parent_dict.get("cell_ontology_term") == annotation.get(
                "cell_ontology_term"
            ):
                annotation.pop("cell_ontology_term_id", None)
                annotation.pop("cell_ontology_term", None)