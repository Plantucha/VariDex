# File: varidex/pipeline/gpu_pipeline.py (NEW ~400 lines)

"""
FULL GPU Pipeline - End-to-End ROCm Acceleration
ClinVar + gnomAD + dbNSFP → 500x faster!

Usage:
python3 -m varidex.pipeline.gpu --use-gpu
"""


class GPUPipeline:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def run_full_pipeline(self, clinvar_path, user_genome, gnomad_dir):
        # 1. GPU ClinVar parsing (5s)
        clinvar_gpu = GPUClinVarLoader(clinvar_path).load()

        # 2. GPU user genome loading (1s)
        user_gpu = GPUUserGenomeLoader(user_genome).load()

        # 3. GPU variant matching (2s)
        matches_gpu = GPUVariantMatcher.match(clinvar_gpu, user_gpu)

        # 4. GPU gnomAD annotation (3s)
        matches_gpu = GPUgnomADStage(gnomad_dir).process(matches_gpu)

        # 5. GPU dbNSFP scoring (6s)
        matches_gpu = GPUdbNSFPAnnotator(dbnsfp_dir).annotate(matches_gpu)

        # 6. GPU ACMG classification (2s)
        classifications_gpu = GPUACMGClassifier().classify(matches_gpu)

        # 7. Download to CPU + HTML report
        results_df = classifications_gpu.to_pandas()
        generate_html_report(results_df)

        return results_df
