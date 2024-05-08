import rdflib

from pathlib import Path
from typing import Union, Optional, List

from cas.linkml.schema import CAS_ROOT_CLASS, DEFAULT_PREFIXES, CAS_NAMESPACE
from cas.file_utils import read_json_file

from linkml_runtime.utils.compile_python import compile_python
from linkml_runtime.linkml_model import SchemaDefinition
from linkml_runtime import SchemaView
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.dumpers import rdflib_dumper
from linkml.validator import Validator
from linkml import generators

CELL_RELATION = "has_cellid"


def dump_to_rdf(
    schema: Union[str, Path, dict],
    instance: Union[str, dict],
    ontology_namespace: str,
    ontology_iri: str,
    labelsets: Optional[List[str]] = None,
    output_path: str = None,
    validate: bool = True,
    include_cells: bool = True,
) -> Optional[rdflib.Graph]:
    """
    Dumps the given data to an RDF file based on the given schema file.
    Args:
        schema: The schema path/dict to be used for the RDF generation.
        instance: The data json file path or json object dict
        ontology_namespace: The namespace of the ontology (such as `MTG`).
        ontology_iri: The IRI of the ontology (such as `https://purl.brain-bican.org/ontology/AIT_MTG/`).
        labelsets: (Optional) The labelsets used in the taxonomy (such as `["Cluster", "Subclass", "Class"]`).
        output_path: (Optional) The output RDF file path.
        validate: (Optional) Boolean to determine if data-schema validation checks will be performed. True by default.
        include_cells: (Optional) Boolean to determine if cell data will be included in the RDF output. True by default.

    Returns:
        RDFlib graph object
    """
    schema_def: SchemaDefinition = yaml_loader.load(
        schema, target_class=SchemaDefinition
    )

    if isinstance(instance, str):
        instance = read_json_file(instance)
    instance = remove_empty_strings(instance)

    if validate:
        validate_data(schema_def, instance)

    gen = generators.PythonGenerator(schema_def)
    output = gen.serialize()
    python_module = compile_python(output)
    py_target_class = getattr(python_module, CAS_ROOT_CLASS)

    try:
        py_inst = py_target_class(**instance)
    except Exception as e:
        print(f"Could not instantiate {py_target_class} from the data; exception: {e}")
        return None

    prefixes = DEFAULT_PREFIXES.copy()
    prefixes["_base"] = ontology_iri
    prefixes[ontology_namespace] = ontology_iri
    for labelset in labelsets:
        prefixes[labelset] = ontology_iri + f"{labelset}#"

    g = rdflib_dumper.as_rdf_graph(
        py_inst,
        schemaview=SchemaView(schema_def),
        prefix_map=prefixes,
    )

    add_cl_existential_restrictions(g)
    if not include_cells:
        g.remove((None, rdflib.URIRef(CAS_NAMESPACE + "/" + CELL_RELATION), None))

    if output_path:
        g.serialize(format="xml", destination=output_path)
    return g


def add_cl_existential_restrictions(g: rdflib.Graph):
    """
    Adds existential restrictions to the CL class in the given RDF graph.
    Args:
        g: The RDF graph to be updated.
    """
    sparql_query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX PCL: <http://purl.obolibrary.org/obo/PCL_>
        PREFIX RO: <http://purl.obolibrary.org/obo/RO_>
        
        
        DELETE {
            ?annotation RO:0002473 ?cl_term .
        }
        INSERT { 
            ?annotation rdf:type [
                a  owl:Restriction ;
               owl:onProperty  RO:0002473 ;
               owl:someValuesFrom ?cl_term
            ] .
        }
        WHERE {
          ?annotation a PCL:0010001.
          ?annotation RO:0002473 ?cl_term .
        }
    """
    g.update(sparql_query)


def validate_data(schema: SchemaDefinition, instance: dict) -> bool:
    """
    Validates the given data instance against the given schema.
    Args:
        schema: The schema to be used for the validation.
        instance: The data instance to be validated.

    Returns:
        Returns `True` if data is valid. Logs the validation errors and raises an exception if data is invalid.
    """
    validator = Validator(schema)
    report = validator.validate(instance)
    if report.results:
        print("Validation errors ({}):".format(len(report.results)))
        for result in report.results:
            print(result)
        raise ValueError(
            "Data file is not valid against the schema. {} validation errors found.".format(
                len(report.results)
            )
        )

    print("Data file is valid against the schema.")
    return True


def populate_ids(
    instance: Union[str, dict], ontology_namespace: str, ontology_id: str
) -> dict:
    """
    Population of id fields in the data instance that are required for the RDF conversion.
    Operation updates the instance object inplace if it is a dict.
    Args:
        instance: The data json file path or json object dict
        ontology_namespace: The namespace of the ontology (such as `MTG`).
        ontology_id: The ontology id to be used for the instance (such as `AIT_MTG`).

    Returns:
        json object with populated id properties
    """
    if isinstance(instance, str):
        data = read_json_file(instance)
        if data is None:
            raise ValueError("No such file: " + instance)
        instance = data

    if "id" in instance and instance["id"]:
        return instance

    if "id" not in instance:
        if "CAS:" not in ontology_id:
            ontology_id = "CAS:" + ontology_id
        instance["id"] = ontology_id

    for labelset in instance.get("labelsets", []):
        if "id" not in labelset:
            labelset["id"] = f"{ontology_namespace}:{labelset['name']}"

    # TODO add id to other properties as well

    return instance


def remove_empty_strings(json_data: dict) -> Union[dict, list]:
    """
    Recursively removes empty strings from the given JSON data.
    Args:
        json_data: The JSON data to be cleaned.

    Returns:
        JSON data with empty strings removed.
    """
    if isinstance(json_data, dict):
        return {
            key: remove_empty_strings(value)
            for key, value in json_data.items()
            if value != ""
        }
    elif isinstance(json_data, list):
        return [remove_empty_strings(item) for item in json_data if item != ""]
    else:
        return json_data
