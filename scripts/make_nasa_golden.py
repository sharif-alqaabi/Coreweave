"""NASA check set: claims transcribed by hand from the OSD-255 primary paper (Mao et al. 2019,
Sci Rep, PMC6746706, "Spaceflight influences gene expression ... in the murine retina"), written
in Helix's lead format and enriched with GeneLab's numbers. Test-only: never train on this file.

    python3 scripts/make_nasa_golden.py OSD-255            -> data/golden/nasa_OSD-255.json (claims without quoted stats)
    python3 scripts/make_nasa_golden.py OSD-255 --numbers  -> data/golden/nasa_OSD-255_numbered.json (paper's padj/log2fc quoted)
    python3 scripts/make_nasa_golden.py OSD-467            -> blind test set from the bone paper (Chowdhury 2021, PMC8509868)
    python3 loop.py --holdout --compare --holdout-file data/golden/nasa_OSD-467.json --group nasa-check

Quoted numbers come from the authors' pipeline and differ from GeneLab's; the critic kills such mismatches
regardless of rules (5/15 false kills on the numbered set vs 0/12 without), so training uses the number-free form.

group = supported      paper claim AND GeneLab padj<0.05 same direction   -> critic must pass
        borderline     GeneLab padj 0.05-0.06 (fails the 0.05 rule by a hair) -> expected kill
        not_reproduced paper padj<0.1 but GeneLab padj>0.1               -> expected kill
        paper_negative paper says NOT differentially expressed            -> critic must kill
        untestable     imaging/histology finding, not in the table        -> critic must kill
        pathway        GO enrichment claimed by the paper                  -> see label
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helix.critic_payload import Table, enrich

STUDY = {
 "OSD-255": {"csv": "data/raw/OSD-255_differential_expression.csv", "paper": "PMC6746706",
             "where": "in the spaceflight retina compared to ground control",
             "next": "Validate by qPCR in an independent set of spaceflight and ground-control retinas."},
 "OSD-467": {"csv": "data/raw/OSD-467_differential_expression.csv", "paper": "PMC8509868",
             "where": "in cortical bone from hindlimb unloaded mice compared to normally loaded controls",
             "next": "Confirm by Nanostring or qPCR on cortical bone from an independent unloading cohort."},
}
# (symbol, direction, paper_padj, paper_log2fc, group, why_not_known)
GENES_255 = [
 ("Drd4", "up", 4.31e-51, 0.812, "supported", "Drd4, the most significant DEG, is a dopamine receptor that controls circadian rhythm in the mammalian retina; supports spaceflight disrupting circadian rhythm."),
 ("H2bc4", "up", 1.66e-9, 0.526, "supported", "Hist1h2bc (now H2bc4) was previously shown upregulated in the aging retina; spaceflight as a potential model for aging."),
 ("Sag", "down", 3.6e-28, -0.66, "supported", "Sag (S-antigen/arrestin) is a retinitis pigmentosa gene; its change in flight links spaceflight to a known retinal disease program."),
 ("Pcare", "down", 6.6e-7, -0.36, "supported", "Pcare (BC027072) is a retinitis pigmentosa gene not previously reported in spaceflight retina."),
 ("Guca1b", "down", 9.2e-6, -0.35, "supported", "Guca1b is a retinitis pigmentosa gene in the phototransduction recovery pathway."),
 ("Rbp3", "down", 2.6e-5, -0.21, "supported", "Rbp3 is a retinitis pigmentosa gene carrying retinoids between photoreceptors and RPE."),
 ("Ahi1", "up", 1.3e-3, 0.21, "supported", "Ahi1 is a retinitis pigmentosa gene required for photoreceptor outer segment formation."),
 ("Guca1a", "down", 2.9e-3, -0.22, "supported", "Guca1a is a retinitis pigmentosa gene regulating guanylate cyclase in photoreceptors."),
 ("Prpf8", "down", 3.8e-3, -0.16, "supported", "Prpf8 is a splicing-factor retinitis pigmentosa gene, tying the RNA-processing signal to retinal disease."),
 ("Cacna2d4", "up", 6.1e-2, 0.12, "supported", "Cacna2d4 is a retinitis pigmentosa gene encoding a photoreceptor calcium-channel subunit."),
 ("Hmgb3", "down", 1.7e-6, -0.50, "supported", "Hmgb3 is a differentially expressed transcription factor needed for eye development and maintenance."),
 ("Prox1", "down", 3.7e-3, -0.16, "supported", "Prox1 is a differentially expressed transcription factor needed for retinal development."),
 ("Hif1a", "down", 6.4e-3, -0.13, "borderline", "Hif1a inactivation mitigates photoreceptor degeneration under hypoxia-like stress; its downregulation links to oxidative stress."),
 ("Rp1", "up", 8.6e-3, 0.15, "borderline", "Rp1 is a retinitis pigmentosa gene structuring the photoreceptor axoneme."),
 ("Gucy2e", "down", 1.4e-2, -0.18, "borderline", "Gucy2e is a retinitis pigmentosa gene, the photoreceptor guanylate cyclase."),
 ("Pde8a", "up", 4.4e-3, 0.22, "not_reproduced", "Pde8a is in 'negative regulation of oxidative stress-induced cell death'; phosphodiesterase inhibition attenuates oxidative stress."),
 ("Hgf", "down", 9.8e-2, -0.52, "not_reproduced", "Hgf activates an antioxidant pathway; its downregulation links to increased oxidative stress in the retina."),
 ("Pde6b", "down", 8.7e-2, -0.14, "not_reproduced", "Pde6b is a retinitis pigmentosa gene, the rod phosphodiesterase."),
 ("Dhdds", "up", 8.8e-2, 0.14, "not_reproduced", "Dhdds is a retinitis pigmentosa gene in dolichol synthesis."),
 ("Mafg", "up", 7.3e-2, 0.24, "not_reproduced", "Mafg is a differentially expressed transcription factor needed for eye development."),
 ("Isl1", "up", 6.1e-3, 0.23, "not_reproduced", "Isl1 is a differentially expressed transcription factor needed for retinal development."),
 ("Atf5", "down", 6.1e-2, -0.58, "not_reproduced", "Atf5 is a differentially expressed transcription factor needed for eye development."),
 ("Kdm6b", "up", 3.5e-2, 0.17, "not_reproduced", "Kdm6b regulates H3K27me2/me3, suggesting spaceflight changes chromatin organization."),
 ("Casz1", "up", 2.5e-2, 0.21, "not_reproduced", "Casz1 is a heterochromatin regulator acting in a splice-variant-specific manner."),
 ("Kdm4a", "down", 1.5e-2, -0.26, "not_reproduced", "Kdm4a regulates H3K9me2/me3, an indicator of constitutive heterochromatin."),
 ("Abca4", "up", None, None, "paper_negative", "Abca4 is shared between retinitis pigmentosa and macular degeneration gene sets."),
 ("Nmnat1", "up", None, None, "paper_negative", "Nmnat1 is shared between two retinal disease gene sets."),
 ("Casp3", "up", None, None, "paper_negative", "Casp3 is shared between two retinal disease gene sets."),
 ("Crb1", "down", None, None, "paper_negative", "Crb1 is shared between two retinal disease gene sets."),
]

OTHER_255 = [  # (id, shape, rows, claim, group, label, why_not_known, next_step)
 ("thickness", "global_pattern", [], "Total retina, retinal pigment epithelium, and choroid layers decreased significantly in thickness (p < 0.05) during spaceflight.", "untestable", "untestable",
  "MicroCT shows structural loss of retinal layers after 35 days of flight.", "Repeat MicroCT thickness measurement on additional flight retinas."),
 ("cones", "global_pattern", [], "Cone photoreceptor density showed a strong trend decrease in spaceflight mice (950 vs 1199 counts/mm2, p = 0.06).", "untestable", "untestable",
  "PNA staining suggests cone photoreceptor degradation during spaceflight.", "Quantify PNA-positive cones in a larger cohort."),
 ("go_vision", "pathway", ["GO:0007601"], "Genes for visual perception (GO:0007601) are overrepresented among spaceflight differentially expressed genes.", "pathway", "ok",
  "Ocular-function categories were the most enriched among the 600 DEGs.", "Test phototransduction gene expression by qPCR and ERG in flight retinas."),
 ("go_rna", "pathway", ["GO:0006396"], "Genes for RNA processing (GO:0006396) are overrepresented among spaceflight differentially expressed genes.", "pathway", "ok",
  "RNA processing and splicing categories were enriched, a signal not tied to retinal disease genes.", "Check splicing-factor protein levels in flight retinas."),
 ("go_radiation", "pathway", ["GO:0009314"], "Genes responding to radiation (GO:0009314) are overrepresented among spaceflight differentially expressed genes.", "pathway", "ok",
  "Direct response to the physical pressures of spaceflight, including radiation.", "Compare with ground irradiation retina datasets."),
]


GENES_467 = [  # Chowdhury et al. 2021: 13 RNAseq DEGs at padj<0.1 (4 named) + Nanostring-confirmed upregulated genes
 ("Pfkfb3", "up", 0.1, 0.85, "supported", "Pfkfb3 (1.8-fold by Nanostring) links unloading to glycolytic flux in bone; monosaccharide metabolism was the top enriched process."),
 ("Igfbp5", "up", 0.1, None, "not_reproduced", "Igfbp5 is an IGF-axis regulator of bone formation, enriched in monosaccharide and protein metabolism terms."),
 ("Stfa1", "up", 0.1, None, "not_reproduced", "Stfa1 (stefin A1) points to peptidase inhibition as an unloading response in bone."),
 ("Stfa2", "up", 0.1, None, "not_reproduced", "Stfa2 (stefin A2) points to peptidase inhibition as an unloading response in bone."),
 ("Scd1", "up", 0.01, 1.0, "not_reproduced", "Scd1 (2-fold by Nanostring) links unloading to lipid metabolism in bone."),
 ("Fzd4", "up", 0.03, 0.68, "not_reproduced", "Fzd4 is a Wnt receptor; Wnt signaling was implicated in the unloading response."),
 ("Mmp3", "up", 0.007, 0.85, "not_reproduced", "Mmp3 drives matrix remodeling during bone loss."),
 ("Sfrp2", "up", 0.05, 0.77, "not_reproduced", "Sfrp2 is a secreted Wnt antagonist, consistent with reduced bone formation."),
 ("Sfrp4", "up", 0.009, 0.77, "not_reproduced", "Sfrp4 is a secreted Wnt antagonist, consistent with reduced bone formation."),
 ("Mmp13", "up", 0.01, 0.68, "not_reproduced", "Mmp13 is an osteocyte collagenase active in perilacunar remodeling."),
 ("Bmp4", "up", 0.02, 0.49, "not_reproduced", "Bmp4 is a bone morphogenetic protein in the unloading response."),
 ("Timp1", "up", 0.02, 0.58, "not_reproduced", "Timp1 balances Mmp activity during remodeling."),
 ("Npy", "up", 0.04, 0.26, "not_reproduced", "Npy links neural signaling to bone mass regulation."),
 ("Spp1", "up", 0.02, 0.58, "not_reproduced", "Spp1 (osteopontin) marks osteoclast-mediated resorption."),
 ("Alpl", "down", None, None, "paper_negative", "Alpl is an osteoblast marker on the Nanostring panel; the paper detected no downregulated genes."),
 ("Acp5", "down", None, None, "paper_negative", "Acp5 (TRAP) is an osteoclast marker on the Nanostring panel; the paper detected no downregulated genes."),
 ("Aspn", "down", None, None, "paper_negative", "Aspn is a matrix gene on the Nanostring panel; the paper detected no downregulated genes."),
]
OTHER_467 = [
 ("nanostring_corr", "global_pattern", [], "Transcript abundances measured by RNAseq and Nanostring correlate strongly in control cortical bone (Pearson R = 0.90).", "untestable", "untestable",
  "Cross-platform agreement validates the RNAseq measurements.", "Repeat Nanostring on additional control samples."),
 ("go_monosacch", "pathway", ["GO:0005996"], "Monosaccharide metabolic process genes (GO:0005996) are overrepresented among unloading differentially expressed genes.", "not_reproduced", "contradicted",
  "Metabolic reprogramming of bone under unloading is not the textbook resorption story.", "Measure glycolytic enzyme activity in unloaded cortical bone."),
 ("go_wnt", "pathway", ["GO:0016055"], "Wnt signaling pathway genes (GO:0016055) are overrepresented among unloading differentially expressed genes.", "not_reproduced", "contradicted",
  "Wnt signaling was implicated by both RNAseq and Nanostring.", "Assay beta-catenin activity in unloaded bone."),
]
SETS = {"OSD-255": (GENES_255, OTHER_255), "OSD-467": (GENES_467, OTHER_467)}

def main(study, numbers=False):
    cfg = STUDY[study]; genes, other = SETS[study]
    table = Table(cfg["csv"])
    leads = []
    for i, (sym, d, pp, plfc, group, why) in enumerate(genes, 1):
        verb = "upregulated" if d == "up" else "downregulated"
        num = f" (adjusted p-value {pp:.2e}; log2 fold-change {plfc:+.3f})" if numbers and pp and plfc else ""
        claim = f"{sym} is {verb} {cfg['where']}{num}."
        label = "ok" if group == "supported" else "contradicted"
        note = {"supported": "paper claim; GeneLab agrees at padj<0.05", "borderline": "paper claim; GeneLab padj just above 0.05",
                "not_reproduced": f"paper padj {pp or 0:.1e}; GeneLab does not reproduce at padj<0.1",
                "paper_negative": "paper explicitly reports this gene is NOT differentially expressed"}[group]
        leads.append({"id": f"{study}_nasa_{i:02d}", "shape": "single_gene", "claim": claim, "rows": [sym],
                      "why_not_known": why, "next_step": cfg["next"], "dataset": study, "group": group,
                      "paper": {"padj": pp, "log2fc": plfc}, "label": label, "label_note": note})
    for i, (tag, shape, rows, claim, group, label, why, nxt) in enumerate(other, len(genes) + 1):
        leads.append({"id": f"{study}_nasa_{i:02d}_{tag}", "shape": shape, "claim": claim, "rows": rows,
                      "why_not_known": why, "next_step": nxt, "dataset": study, "group": group,
                      "paper": {}, "label": label, "label_note": "paper claim (" + group + ")"})
    enrich(leads, table)
    out = f"data/golden/nasa_{study}{'_numbered' if numbers else ''}.json"
    json.dump(leads, open(out, "w"), indent=1)
    for l in leads:
        print(f"{l['id']:28} {l['group']:14} {l['label']:12}", {k: {kk: v[kk] for kk in ("log2fc", "padj", "carriers") if kk in v} if "error" not in v else v for k, v in l["table_facts"].items()} or "")
    print(len(leads), "leads ->", out)


if __name__ == "__main__":
    main(sys.argv[1], numbers="--numbers" in sys.argv)
