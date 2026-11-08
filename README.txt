VCE - Supplementary Data
VCE: Efficient Native Configuration Deployment Recovery Using Validated Completion Evidence

READ
generated/S1_Validation_and_Statistics.txt  Primary statistics and validation index
generated/S2_Scale_Results.txt             Scale/layout experiment and complete tables
The same documents are supplied as Markdown (.md). TXT is provided for readers
without a Markdown viewer. The new S1/S2 documents use plain text and tables.

REGENERATE (Python 3.10 or newer; standard library only)
1. Extract the complete ZIP.
2. Run: python generate_supplements.py
3. Open generated/S1_Validation_and_Statistics.txt and generated/S2_Scale_Results.txt.
   The script also writes the Markdown files, 16 CSV/JSON tables, input hashes,
   and GENERATION_REPORT.json. It needs no network, model endpoint, or extra packages.
4. To compare saved outputs without writing: python generate_supplements.py --check
5. To rebuild the documents, file manifest, and ZIP: python build_package.py
   The resulting VCE_Supplementary_Data.zip is written beside the extracted folder.

CONTENTS
generated/               Current S1/S2 in MD and TXT, plus numerical/source tables
Research_Artifact/        Retained research distribution, source, and observations
Historical_Evidence/      Separate earlier runtime records and version/setup notes
generate_supplements.py  Data-to-table/document generator
build_package.py         Regeneration and ZIP-building entry
FILE_MANIFEST.csv        Relative path, byte size, and SHA-256 for packaged files

OUTPUT BASIS
The script recomputes primary absolute medians, paired point estimates,
leave-one-input/batch ranges, mean path costs, thresholds, and scale medians.
Confidence limits are read from the saved bootstrap analysis rather than
recomputed with a different bootstrap implementation. The nineteen source-audit
groups are exported from recorded manual assessments. They are not automatic
source proofs. generated/SOURCE_MANIFEST.csv identifies every input file.

Raw experiment observations are inputs. These commands do not generate new
measurements, rerun the native experiments, or replace the archived records.
Native-experiment reruns have additional requirements described in
Research_Artifact/README.md and its dependency/provenance files.

VERSION SCOPE
Use generated/S1_Validation_and_Statistics.* and generated/S2_Scale_Results.*
as the current supplements. Research_Artifact/manuscript/ contains only plotting code and figure-data inputs
required by the preserved research tools. Article text and author images are
excluded from this public code/data distribution. The main manuscript is
uploaded separately. Historical data, source hashes, labels, and nested release
manifests retain their original scope. FILE_MANIFEST.csv at this root describes
this assembled package and excludes itself.

Contact: Shujuan Tian, sjtianwork@xtu.edu.cn
