### Notes on Tutorial:

WMB-demo.ipynb - Ugur's interpretation of this ticket: https://github.com/cellannotation/cas-tools/issues/143
CAS_Tutorial.ipynb - New tutorial doc with extensive markerdown - follows starting points structure detailed below.

Work so far: 
1. File issues
   1. WMB CB Glut - http://cellular-semantics.cog.sanger.ac.uk/public/merged_CS20230722_CLAS_29.h5ad issues:
     1. Doesn't have Neurotransmitter labelset
     1. Limited metadata (no ontology IDs for anything except tissue)
     2. Only ENSEMBL Gene IDs in var - non-standard field name --> better to modify to CxG standard?
     3. Should be updated from lastest CAS (which needs cluster metadata)
     4. UMAP embedding name doesn't work with scanpy default standard (X-UMAP --> umap)
        
2. CAS functionality needed.
   3. cas flatten should use cas in head by default.
   4. cas flatten should store cas in header
   5. flatten - rename to export2CAP + should only flatten CAP fields
   6. It should be possible to update with obs<->cas without going through a flattening step

5. Starting points:
    1. Intro - what is CAS / CAS-tools + show pre-rolled h5ad file in use
         1. Reporting
         2. Add a column (author annotation) https://github.com/cellannotation/cas-tools/blob/main/docs/cli.md#add-author-annotations-to-cas-json
         3. Export to CAP Needs intro text to explain - !cas flatten (Currently needs separate file)
    3. CxG dataset
         1. Generate CAS from Anndata (e.g. from CxG) https://github.com/cellannotation/cas-tools/blob/main/docs/cli.md#convert-anndata-to-cas --> embedded h5ad file 
    2. Allen style taxonomy spreadsheet + h5ad (we should also point users to TDT repo). HKIR will do this, using WMB example
       1. Generate CAS
       2. Validate CAS against h5ad
       3. Populate IDs
       4. Merge
    4. CAS repo --> point to TDT doc for this.
    5. Roundtripping  See existing NB CAS-CAP round-tripping demo.ipynb - Needs better annotation.
    
   
6. To Demo:
   4.  Export to CAP

7. 